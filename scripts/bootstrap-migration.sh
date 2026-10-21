#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Usage: $0 --workspace ABSOLUTE_DIR --local-repository ABSOLUTE_DIR [--goal test-compile|package|install]"
}
workspace=''
local_repository=''
goal='install'
offline=false
resume_from=''
settings=''
while (($#)); do
  case "$1" in
    --workspace) [[ $# -ge 2 && -z "$workspace" ]] || { usage >&2; exit 2; }; workspace=$2; shift 2 ;;
    --local-repository) [[ $# -ge 2 && -z "$local_repository" ]] || { usage >&2; exit 2; }; local_repository=$2; shift 2 ;;
    --resume-from) [[ $# -ge 2 ]] || exit 2; resume_from=$2; shift 2 ;;
    --settings) [[ $# -ge 2 ]] || exit 2; settings=$2; shift 2 ;;
    --offline) offline=true; shift ;;
    --goal) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; goal=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ "$workspace" == /* && "$local_repository" == /* ]] || { usage >&2; exit 2; }
case "$goal" in test-compile|package|install) ;; *) echo "Unsupported safe build goal: $goal" >&2; exit 2 ;; esac
workspace="$(cd "$workspace" && pwd -P)" || exit 2
for repo in Stellar-Enclosure-Parent Stellar-Enclosure-Components Stellar-Enclosure-COLA tianshu-service yuheng-service yaoguang-service tianquan-jianshen-service tianquan-shoubing-service; do
  [[ -d "$workspace/$repo/.git" ]] || { echo "Missing repository: $repo" >&2; exit 2; }
done
case "$local_repository/" in "$workspace/"|"$workspace/"*/.git/*) echo "Unsafe cache directory" >&2; exit 2 ;; esac
mkdir -p "$workspace/.migration" "$local_repository"
lock="$local_repository/.stellar-bootstrap.lock"
mkdir "$lock" 2>/dev/null || { echo "Bootstrap already owns this cache: $lock" >&2; exit 2; }
reactor_dir="$(mktemp -d "$workspace/.migration/bootstrap.XXXXXX")"
cleanup() {
  rmdir "$lock" 2>/dev/null || true
}
trap cleanup EXIT
mvn="$workspace/Stellar-Enclosure-Parent/mvnw"
args=(-B -ntp "-Dmaven.repo.local=$local_repository" -DskipTests -DskipITs -Dinvoker.skip=true -Darchetype.test.skip=true)
if $offline; then args+=(--offline); fi
if [[ -n "$settings" ]]; then [[ "$settings" == /* && -r "$settings" ]] || exit 2; args+=(--settings "$settings"); fi
seed() {
  artifact="$(python3 - "$workspace/$1" <<'PYID'
from xml.etree import ElementTree as E
import sys
print(E.parse(sys.argv[1]).getroot().findtext('{http://maven.apache.org/POM/4.0.0}artifactId'))
PYID
)"
  installed="$local_repository/top/egon/$artifact/0.0.1/$artifact-0.0.1.pom"
  if cmp -s "$workspace/$1" "$installed"; then
    echo "SEED CACHED $1"
    return
  fi
  echo "SEED $1"
  "$mvn" "${args[@]}" -N -f "$workspace/$1" install || exit 1
}
seed Stellar-Enclosure-Parent/pom.xml
seed Stellar-Enclosure-Components/stellar-enclosure-components-bom/pom.xml
seed Stellar-Enclosure-Parent/platform-parent/pom.xml
seed Stellar-Enclosure-Components/pom.xml
for repo in tianshu-service yuheng-service yaoguang-service tianquan-jianshen-service tianquan-shoubing-service; do
  seed "$repo/pom.xml"
done
seed Stellar-Enclosure-COLA/stellar-enclosure-archetypes/pom.xml
python3 - "$workspace" "$reactor_dir/pom.xml" <<'PY'
from pathlib import Path
from xml.sax.saxutils import escape
import sys, os
workspace=Path(sys.argv[1])
paths=['Stellar-Enclosure-Components','tianshu-service','yuheng-service','yaoguang-service','tianquan-jianshen-service','tianquan-shoubing-service','Stellar-Enclosure-COLA/stellar-enclosure-archetypes/source-projects']
modules=''.join('        <module>'+escape(os.path.relpath(workspace/p,Path(sys.argv[2]).parent))+'</module>\n' for p in paths)
Path(sys.argv[2]).write_text('''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>top.egon.internal.migration</groupId>
    <artifactId>stellar-enclosure-bootstrap</artifactId>
    <version>0.0.1</version>
    <packaging>pom</packaging>
    <properties><maven.deploy.skip>true</maven.deploy.skip></properties>
    <modules>
'''+modules+'''    </modules>
</project>
''')
PY
if [[ -n "$resume_from" ]]; then
  [[ "$resume_from" =~ ^:stellar-enclosure-[a-z0-9-]+$ ]] || exit 2
  args+=(--resume-from "$resume_from")
fi
echo "BUILD goal=$goal workspace=$workspace reactor=$reactor_dir/pom.xml"
"$mvn" "${args[@]}" -f "$reactor_dir/pom.xml" "$goal"
echo "PASS bootstrap goal=$goal; tests requiring runtimes were not executed."
