#!/usr/bin/env python3
"""Prepare the explicit first-release order from the migrated POMs."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from xml.etree import ElementTree as ET

NS={'m':'http://maven.apache.org/POM/4.0.0'}
def prepare(workspace: Path) -> list[dict]:
    projects={}
    models={}
    roots=['Stellar-Enclosure-Parent','Stellar-Enclosure-Components','Stellar-Enclosure-COLA','tianshu-service','yuheng-service','yaoguang-service','tianquan-jianshen-service','tianquan-shoubing-service']
    for repo in roots:
        for path in (workspace/repo).rglob('pom.xml'):
            relative=path.relative_to(workspace)
            if any(x.startswith('.generated.') for x in relative.parts):continue
            if any(x in relative.parts for x in ['target','.git','src','node_modules','archetype-resources','plugin-output']):continue
            root=ET.parse(path).getroot()
            artifact=root.findtext('m:artifactId',default='',namespaces=NS)
            if not artifact.startswith('stellar-enclosure-') or artifact=='stellar-enclosure-cola':continue
            source='source-projects' in relative.parts
            if artifact in models:raise ValueError('Duplicate artifact: '+artifact)
            models[artifact]=(relative,root,source)

    def inherited(artifact, visiting=frozenset()):
        if artifact not in models:return {},set()
        if artifact in visiting:raise ValueError('Parent cycle: '+artifact)
        root=models[artifact][1]
        parent=root.findtext('m:parent/m:artifactId',namespaces=NS)
        properties,excluded=inherited(parent,visiting|{artifact})
        properties=dict(properties)
        properties.update({p.tag.split('}')[-1]:p.text or '' for p in root.findall('m:properties/*',NS)})
        excluded=excluded|{e.text for e in root.findall(".//m:plugin[m:artifactId='central-publishing-maven-plugin']/m:configuration/m:excludeArtifacts/m:excludeArtifact",NS)}
        return properties,excluded

    for artifact,(relative,root,source) in models.items():
        if source and not artifact.endswith('-facade'):continue
        properties,excluded=inherited(artifact)
        if properties.get('maven.deploy.skip')=='true' or artifact in excluded:continue

        def resolve(value):
            for _ in range(len(properties)+1):
                expanded=re.sub(r'\$\{([^}]+)\}',lambda m:properties.get(m[1],m[0]),value)
                if expanded==value:break
                value=expanded
            if '${' in value:raise ValueError('Unresolved coordinate for '+artifact+': '+value)
            return value

        group=root.findtext('m:groupId',namespaces=NS) or root.findtext('m:parent/m:groupId',namespaces=NS)
        if not group or not group.startswith('top.egon'):continue
        group=resolve(group)
        version=resolve(root.findtext('m:version',namespaces=NS) or root.findtext('m:parent/m:version',namespaces=NS) or '')
        if not version:raise ValueError('Missing version for '+artifact)
        dependencies=set()
        parent=root.findtext('m:parent/m:artifactId',namespaces=NS)
        if parent:dependencies.add(parent)
        for dep in root.findall('m:dependencies/m:dependency',NS):
            aid=dep.findtext('m:artifactId',namespaces=NS)
            if aid:dependencies.add(aid)
        for dep in root.findall('m:dependencyManagement/m:dependencies/m:dependency',NS):
            if dep.findtext('m:scope',namespaces=NS)=='import':
                aid=dep.findtext('m:artifactId',namespaces=NS)
                if aid:dependencies.add(aid)
        for plugin in root.findall('m:build/m:plugins/m:plugin',NS):
            aid=plugin.findtext('m:artifactId',namespaces=NS)
            if aid:dependencies.add(aid)
        item={'repository':relative.parts[0],'pom':relative.as_posix(),'groupId':group,'artifactId':artifact,'version':version,'packaging':root.findtext('m:packaging',default='jar',namespaces=NS),'resolvedFacade':source,'dependsOn':sorted(dependencies)}
        if artifact in projects and projects[artifact]['pom']!=item['pom']:raise ValueError('Duplicate artifact: '+artifact)
        projects[artifact]=item
    known=set(projects)
    graph={aid:set(item['dependsOn'])&known-{aid} for aid,item in projects.items()}
    output=[];done=set()
    while len(done)<len(projects):
        ready=sorted(aid for aid in known-done if graph[aid]<=done)
        if not ready:raise ValueError('Public artifact dependency cycle: '+', '.join(sorted(known-done)))
        for aid in ready:
            item=projects[aid];item['dependsOn']=sorted(graph[aid]);output.append(item)
        done.update(ready)
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.workspace.is_absolute() or not args.output.is_absolute():parser.error('absolute paths are required')
    projects=prepare(args.workspace.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'version':'0.0.1','namespace':'top.egon','projects':projects},indent=2)+'\n')
    print('Prepared release order for',len(projects),'artifacts')
if __name__=='__main__':main()
