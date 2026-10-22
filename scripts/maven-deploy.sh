#!/usr/bin/env bash
set -Eeuo pipefail
workspace=''
local_repository=''
mode='--dry-run'
while (($#)); do
  case "$1" in
    --workspace) [[ $# -ge 2 ]] || exit 2; workspace=$2; shift 2 ;;
    --local-repository) [[ $# -ge 2 ]] || exit 2; local_repository=$2; shift 2 ;;
    --dry-run|--publish) mode=$1; shift ;;
    *) echo "Usage: $0 --workspace ABS --local-repository ABS [--dry-run|--publish]" >&2; exit 2 ;;
  esac
done
if [[ "$mode" == '--publish' ]]; then
  echo "Workspace-wide publication has been retired. Use the independent publication commands in each repository's README.md." >&2
  exit 2
fi
[[ "$workspace" == /* && "$local_repository" == /* ]] || exit 2
workspace="$(cd "$workspace" && pwd -P)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
manifest="$script_dir/../release/maven-release-order.json"
bash "$script_dir/bootstrap-workspace.sh" --workspace "$workspace" --local-repository "$local_repository"
cola="$workspace/Stellar-Enclosure-COLA"
(cd "$cola" && ./scripts/generate_archetypes.sh generate && ./scripts/generate_archetypes.sh check)
python3 "$script_dir/maven-release-order.py" --workspace "$workspace" --output "$manifest"
mvn="$workspace/Stellar-Enclosure-Parent/mvnw"
if [[ "$mode" == '--dry-run' ]]; then
  python3 - "$workspace" "$manifest" "$local_repository" "$mvn" <<'PY'
from pathlib import Path
from xml.sax.saxutils import escape
import json,os,subprocess,sys,tempfile
workspace=Path(sys.argv[1]);manifest=json.loads(Path(sys.argv[2]).read_text())
roots=['Stellar-Enclosure-Parent','Stellar-Enclosure-Parent/platform-parent','Stellar-Enclosure-Components','tianshu-service','yuheng-service','yaoguang-service','tianquan-jianshen-service','tianquan-shoubing-service','Stellar-Enclosure-COLA/stellar-enclosure-archetypes']
with tempfile.TemporaryDirectory(prefix='stellar-release.') as temporary:
    directory=Path(temporary).resolve()
    modules=''.join('<module>'+escape(os.path.relpath(workspace/p,directory))+'</module>' for p in roots)
    pom=directory/'pom.xml'
    pom.write_text('<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion><groupId>top.egon.internal.build</groupId><artifactId>stellar-enclosure-release-check</artifactId><version>0.0.1</version><packaging>pom</packaging><modules>'+modules+'</modules></project>')
    subprocess.run([sys.argv[4],'-B','-ntp','-f',str(pom),'-Dmaven.repo.local='+sys.argv[3],'-Prelease','-Pgenerated-archetypes','-DskipTests','-DskipITs','-Dinvoker.skip=true','-Darchetype.test.skip=true','-Dgpg.skip=true','verify'],check=True)
print('PASS release dry-run; no artifacts were published.')
PY
fi
