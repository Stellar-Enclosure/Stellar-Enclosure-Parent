import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'maven-release-order.py'
spec = importlib.util.spec_from_file_location('maven_release_order', SCRIPT)
release_order = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_order)


class MavenReleaseOrderTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = Path(self.directory.name)

    def pom(self, path, artifact, content=''):
        target = self.workspace / path / 'pom.xml'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('<project xmlns="http://maven.apache.org/POM/4.0.0">'
                          '<modelVersion>4.0.0</modelVersion>'
                          '<artifactId>' + artifact + '</artifactId>' + content + '</project>')

    def test_inherited_skip_excludes_entire_test_reactor(self):
        self.pom('yuheng-service', 'stellar-enclosure-yuheng',
                 '<groupId>top.egon</groupId><version>1.2.3</version>')
        self.pom('yuheng-service/tests', 'stellar-enclosure-yuheng-test',
                 '<parent><groupId>top.egon</groupId><artifactId>stellar-enclosure-yuheng</artifactId>'
                 '<version>1.2.3</version></parent>'
                 '<properties><maven.deploy.skip>true</maven.deploy.skip></properties>')
        self.pom('yuheng-service/tests/provider', 'stellar-enclosure-yuheng-test-provider',
                 '<parent><groupId>top.egon</groupId><artifactId>stellar-enclosure-yuheng-test</artifactId>'
                 '<version>1.2.3</version></parent>')
        projects = release_order.prepare(self.workspace)
        self.assertEqual(['stellar-enclosure-yuheng'], [p['artifactId'] for p in projects])
        self.assertEqual('1.2.3', projects[0]['version'])

    def test_central_exclusion_is_inherited_and_order_preserves_parent(self):
        self.pom('tianshu-service', 'stellar-enclosure-tianshu',
                 '<groupId>top.egon</groupId><version>2.0.0</version>'
                 '<build><pluginManagement><plugins><plugin>'
                 '<artifactId>central-publishing-maven-plugin</artifactId>'
                 '<configuration><excludeArtifacts>'
                 '<excludeArtifact>stellar-enclosure-tianshu-admin</excludeArtifact>'
                 '</excludeArtifacts></configuration></plugin></plugins></pluginManagement></build>')
        for name in ['admin', 'starter']:
            self.pom('tianshu-service/' + name, 'stellar-enclosure-tianshu-' + name,
                     '<parent><groupId>top.egon</groupId><artifactId>stellar-enclosure-tianshu</artifactId>'
                     '<version>2.0.0</version></parent>')
        projects = release_order.prepare(self.workspace)
        self.assertEqual(['stellar-enclosure-tianshu', 'stellar-enclosure-tianshu-starter'],
                         [p['artifactId'] for p in projects])
        self.assertEqual(['stellar-enclosure-tianshu'], projects[1]['dependsOn'])

    def test_facade_resolves_version_from_unpublished_source_parent(self):
        self.pom('Stellar-Enclosure-COLA/source-projects/service', 'stellar-enclosure-source-service',
                 '<groupId>top.egon.internal.archetype.source</groupId>'
                 '<version>${stellar-enclosure.version}</version>'
                 '<properties><stellar-enclosure.version>3.1.0</stellar-enclosure.version></properties>')
        self.pom('Stellar-Enclosure-COLA/source-projects/service/facade', 'stellar-enclosure-source-service-facade',
                 '<parent><groupId>top.egon.internal.archetype.source</groupId>'
                 '<artifactId>stellar-enclosure-source-service</artifactId>'
                 '<version>${stellar-enclosure.version}</version></parent>')
        projects = release_order.prepare(self.workspace)
        self.assertEqual(1, len(projects))
        self.assertEqual('3.1.0', projects[0]['version'])
        self.assertTrue(projects[0]['resolvedFacade'])

    def test_build_only_processor_and_cli_precede_producer(self):
        for name in ['contract', 'processor', 'manifest-cli']:
            dependency = '' if name == 'contract' else (
                '<dependencies><dependency><groupId>top.egon</groupId>'
                '<artifactId>stellar-enclosure-contract</artifactId></dependency></dependencies>')
            self.pom('tianquan-jianshen-service/' + name, 'stellar-enclosure-' + name,
                     '<groupId>top.egon</groupId><version>1</version>' + dependency)
        self.pom('tianshu-service', 'stellar-enclosure-a-producer',
                 '<groupId>top.egon</groupId><version>1</version>'
                 '<profiles><profile><id>permission-producer</id><build><plugins>'
                 '<plugin><artifactId>maven-compiler-plugin</artifactId><executions><execution><configuration>'
                 '<annotationProcessorPaths><path><groupId>top.egon</groupId>'
                 '<artifactId>stellar-enclosure-processor</artifactId></path></annotationProcessorPaths>'
                 '</configuration></execution></executions></plugin>'
                 '<plugin><artifactId>exec-maven-plugin</artifactId><dependencies><dependency>'
                 '<groupId>top.egon</groupId><artifactId>stellar-enclosure-manifest-cli</artifactId>'
                 '</dependency></dependencies></plugin></plugins></build></profile></profiles>')
        projects = release_order.prepare(self.workspace)
        producer = projects[-1]
        self.assertEqual('stellar-enclosure-a-producer', producer['artifactId'])
        self.assertEqual(['stellar-enclosure-manifest-cli', 'stellar-enclosure-processor'], producer['dependsOn'])
        self.assertEqual('stellar-enclosure-contract', projects[0]['artifactId'])


if __name__ == '__main__':
    unittest.main()
