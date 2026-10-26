import datetime
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

WORKSPACE = Path(__file__).resolve().parents[3]
REPOSITORIES = ['tianquan-shoubing-service', 'tianquan-jianshen-service', 'tianshu-service', 'yuheng-service', 'yaoguang-service']
SCRIPT = WORKSPACE / 'tianshu-service/scripts/permission-ci.py'
spec = importlib.util.spec_from_file_location('permission_ci', SCRIPT)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class PermissionCiTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.producer = {'producerId': 'tianshu-java', 'module': 'stellar-enclosure-tianshu-admin',
                         'artifactFile': 'stellar-enclosure-tianshu-admin-exec.jar'}
        self.evidence = {'producerId': 'tianshu-java', 'artifactFile': self.producer['artifactFile'],
                         'artifactDigest': 'a' * 64, 'artifact': {'commit': 'b' * 40, 'buildId': 'ci-7'}}

    def proof(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return {'schemaVersion': 1, 'status': 'READY', 'producerId': 'tianshu-java', 'artifactDigest': 'a' * 64,
                'commit': 'b' * 40, 'buildId': 'ci-7', 'verifiedAt': (now - datetime.timedelta(seconds=10)).isoformat(),
                'expiresAt': (now + datetime.timedelta(seconds=120)).isoformat(),
                'selection': {'producers': [{'producerId': 'tianshu-java', 'qualificationId': '123'}]}}

    def test_repositories_share_adapter_and_have_finite_producers(self):
        for repository in REPOSITORIES:
            self.assertEqual(SCRIPT.read_bytes(), (WORKSPACE / repository / 'scripts/permission-ci.py').read_bytes())
            producers = ci.producer_config(WORKSPACE / repository)
            self.assertEqual(5 if repository == 'yuheng-service' else 1, len(producers))
            pipeline = (WORKSPACE / repository / '.gitlab-ci.yml').read_text()
            self.assertIn('${PERMISSION_SDK_REPOSITORY_URL:-', pipeline)
            self.assertNotIn(repository + 'SITORY', pipeline)


    def test_local_uncommitted_lock_cannot_select_remote_tool_commit(self):
        (self.root / 'permission-toolchain.lock.json').write_text(json.dumps({'mode': 'LOCAL_UNCOMMITTED', 'sdk': {'commit': None}}))
        with self.assertRaisesRegex(ValueError, 'REAL_COMMITTED'):
            ci.run('pin', self.root)

    def test_pr_unprotected_and_disabled_jobs_cannot_register(self):
        cases = [{}, {'PERMISSION_DELIVERY_ENABLED': 'true', 'GITHUB_ACTIONS': 'true', 'GITHUB_REF_PROTECTED': 'true', 'GITHUB_EVENT_NAME': 'pull_request'},
                 {'PERMISSION_DELIVERY_ENABLED': 'true', 'GITLAB_CI': 'true', 'CI_COMMIT_REF_PROTECTED': 'false', 'CI_PIPELINE_SOURCE': 'web'}]
        for env in cases:
            with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ValueError, 'PROTECTED_MANUAL'):
                ci.require_delivery_boundary()
        with patch.dict(os.environ, {'PERMISSION_DELIVERY_ENABLED': 'true', 'GITHUB_ACTIONS': 'true', 'GITHUB_REF_PROTECTED': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch'}, clear=True):
            ci.require_delivery_boundary()

    def test_gitlab_superseded_and_expired_pipeline_cannot_write(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        env = {'PERMISSION_DELIVERY_ENABLED': 'true', 'GITLAB_CI': 'true', 'CI_COMMIT_REF_PROTECTED': 'true',
               'CI_PIPELINE_SOURCE': 'web', 'CI_PIPELINE_CREATED_AT': now.isoformat(), 'CI_COMMIT_BRANCH': 'main', 'CI_COMMIT_SHA': 'a' * 40}
        with patch.dict(os.environ, env, clear=True), patch.object(ci.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='b' * 40 + '\trefs/heads/main')):
            with self.assertRaisesRegex(ValueError, 'SUPERSEDED'):
                ci.require_delivery_boundary()
        env['CI_PIPELINE_CREATED_AT'] = (now - datetime.timedelta(days=2)).isoformat()
        with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ValueError, 'EXPIRED'):
            ci.require_delivery_boundary()

    def test_activation_requires_same_deployed_bytes_build_and_existing_qualification(self):
        self.assertEqual(self.proof()['selection'], ci.assert_readiness(self.proof(), self.producer, self.evidence))
        for key in ['artifactDigest', 'commit', 'buildId', 'producerId', 'status']:
            proof = self.proof(); proof[key] = 'different'
            with self.assertRaisesRegex(ValueError, 'PROOF_MISMATCH'):
                ci.assert_readiness(proof, self.producer, self.evidence)
        proof = self.proof(); proof['selection']['producers'][0].pop('qualificationId')
        with self.assertRaisesRegex(ValueError, 'QUALIFICATION_REQUIRED'):
            ci.assert_readiness(proof, self.producer, self.evidence)

    def test_stale_future_and_unbounded_readiness_cannot_activate(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for start, end in [(-300, -1), (10, 100), (-10, 1000)]:
            proof = self.proof()
            proof['verifiedAt'] = (now + datetime.timedelta(seconds=start)).isoformat()
            proof['expiresAt'] = (now + datetime.timedelta(seconds=end)).isoformat()
            with self.assertRaisesRegex(ValueError, 'READINESS_EXPIRED'):
                ci.assert_readiness(proof, self.producer, self.evidence)

    def test_pending_status_is_preserved_without_new_operation_or_retry(self):
        (self.root / 'permission-toolchain.lock.json').write_text('{"mode":"PINNED_COMMIT"}')
        (self.root / 'permission-producers.json').write_text(json.dumps({'schemaVersion': 1, 'producers': [self.producer]}))
        directory = self.root / 'build' / self.producer['module'] / 'target/permissions'
        directory.mkdir(parents=True)
        (directory / 'artifact-evidence.json').write_text(json.dumps(self.evidence))
        env = {'PERMISSION_SDK_ROOT': str(self.root / 'sdk'), 'PERMISSION_BUILD_ROOT': str(self.root / 'build'),
               'PERMISSION_OUTPUT_ROOT': str(self.root / 'result'), 'PERMISSION_DELIVERY_ENABLED': 'true',
               'GITHUB_ACTIONS': 'true', 'GITHUB_REF_PROTECTED': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
               'PERMISSION_PRODUCER_ID': 'tianshu-java', 'PERMISSION_TARGET': 'test',
               'PERMISSION_EXPECTED_PRODUCER_REVISION': '2', 'PERMISSION_EXPECTED_ACTIVE_REVISION': '3',
               'PERMISSION_OPERATION_ID': 'b48058d5-cc1c-4675-8131-3e2d5b3b09e9'}
        with patch.dict(os.environ, env, clear=True), patch.object(ci.subprocess, 'run', return_value=SimpleNamespace(returncode=6)) as invoke:
            self.assertEqual(6, ci.run('register', self.root))
        invoke.assert_called_once()
        args = invoke.call_args.args[0]
        self.assertEqual(env['PERMISSION_OPERATION_ID'], args[args.index('--operation-id') + 1])
        self.assertNotIn('--client-secret', args)

    def test_local_online_mode_rejects_before_any_credential_or_http_access(self):
        (self.root / 'permission-toolchain.lock.json').write_text('{"mode":"LOCAL_UNCOMMITTED"}')
        for phase in ['register', 'activate']:
            with patch.object(ci, 'private_read_token') as credential, patch.object(ci, 'gitlab_read') as network:
                with self.assertRaisesRegex(ValueError, 'LOCAL_TOOLCHAIN_ONLINE_FORBIDDEN'):
                    ci.run(phase, self.root)
                credential.assert_not_called(); network.assert_not_called()

    def test_gitlab_activation_requires_trusted_job_pipeline_and_original_artifact(self):
        proof = self.proof(); proof['gitlab'] = {'projectId': '11', 'pipelineId': '22', 'jobId': '33'}
        now = datetime.datetime.now(datetime.timezone.utc)
        job = {'id': 33, 'name': 'deploy-qualified', 'status': 'success', 'ref': 'main', 'tag': False,
               'erased_at': None, 'commit': {'id': 'b' * 40}, 'pipeline': {'id': 22}, 'finished_at': now.isoformat()}
        pipeline = {'id': 22, 'status': 'success', 'sha': 'b' * 40, 'ref': 'main', 'source': 'web'}
        env = {'GITLAB_CI': 'true', 'CI_PROJECT_ID': '11', 'CI_API_V4_URL': 'https://gitlab.example/api/v4',
               'CI_SERVER_URL': 'https://gitlab.example', 'CI_COMMIT_BRANCH': 'main', 'CI_JOB_NAME': 'permission-activate',
               'PERMISSION_DEPLOYMENT_JOB_NAME': 'deploy-qualified'}
        with patch.dict(os.environ, env, clear=True), patch.object(ci, 'private_read_token', return_value='private-read-token'), \
                patch.object(ci, 'gitlab_read', side_effect=[job, pipeline, proof]) as read:
            ci.verify_gitlab_deployment(proof, self.evidence)
            self.assertEqual(3, read.call_count)
            self.assertTrue(read.call_args.args[0].endswith('/jobs/33/artifacts/permission-deployment.json'))
            self.assertTrue(read.call_args.kwargs['artifact'])
        for changed in [{'status': 'canceled'}, {'name': 'build-and-unit-tests'}, {'ref': 'other'}, {'commit': {'id': 'c' * 40}}]:
            wrong = dict(job); wrong.update(changed)
            with patch.dict(os.environ, env, clear=True), patch.object(ci, 'private_read_token', return_value='secret'), \
                    patch.object(ci, 'gitlab_read', return_value=wrong), self.assertRaisesRegex(ValueError, 'JOB_MISMATCH'):
                ci.verify_gitlab_deployment(proof, self.evidence)
        with patch.dict(os.environ, env, clear=True), patch.object(ci, 'private_read_token', return_value='secret'), \
                patch.object(ci, 'gitlab_read', side_effect=[job, dict(pipeline, status='canceled')]), \
                self.assertRaisesRegex(ValueError, 'PIPELINE_MISMATCH'):
            ci.verify_gitlab_deployment(proof, self.evidence)
        with patch.dict(os.environ, env, clear=True), patch.object(ci, 'private_read_token', return_value='secret'), \
                patch.object(ci, 'gitlab_read', side_effect=[job, pipeline, dict(proof, artifactDigest='c' * 64)]), \
                self.assertRaisesRegex(ValueError, 'ARTIFACT_MISMATCH'):
            ci.verify_gitlab_deployment(proof, self.evidence)

    def test_gitlab_cannot_redirect_read_token_to_a_proof_supplied_origin(self):
        proof = self.proof(); proof['gitlab'] = {'projectId': '11', 'pipelineId': '22', 'jobId': '33'}
        env = {'GITLAB_CI': 'true', 'CI_PROJECT_ID': '11', 'CI_API_V4_URL': 'https://other.example/api/v4',
               'CI_SERVER_URL': 'https://gitlab.example'}
        with patch.dict(os.environ, env, clear=True), patch.object(ci, 'private_read_token') as credential:
            with self.assertRaisesRegex(ValueError, 'API_ORIGIN_INVALID'):
                ci.verify_gitlab_deployment(proof, self.evidence)
            credential.assert_not_called()
        proof['gitlab']['projectId'] = '99'
        with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ValueError, 'PROVENANCE_REQUIRED'):
            ci.verify_gitlab_deployment(proof, self.evidence)

    def test_gitlab_read_token_is_private_and_never_forwarded_to_artifact_cdn(self):
        token = self.root / 'read-token'; token.write_text('private-read-token'); token.chmod(0o600)
        with patch.dict(os.environ, {'PERMISSION_GITLAB_READ_TOKEN_FILE': str(token)}, clear=True):
            self.assertEqual('private-read-token', ci.private_read_token())
            token.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'PRIVATE_READ_TOKEN_REQUIRED'):
                ci.private_read_token()
        import io
        import urllib.error
        error = urllib.error.HTTPError('https://gitlab.example/artifact', 302, 'redirect',
                                       {'Location': 'https://storage.example/proof?signature=private-capability'}, io.BytesIO())
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response; response.status = 200; response.read.return_value = b'{"status":"READY"}'
        opener = unittest.mock.Mock(); opener.open.side_effect = [error, response]
        with patch.object(ci.urllib.request, 'build_opener', return_value=opener):
            self.assertEqual({'status': 'READY'}, ci.gitlab_read('https://gitlab.example/artifact', 'private-read-token', artifact=True))
        first, second = [call.args[0] for call in opener.open.call_args_list]
        self.assertIn('private-read-token', first.headers.values())
        self.assertNotIn('private-read-token', second.headers.values())
        self.assertFalse(any(key.lower() in {'private-token', 'authorization'} for key in second.headers))

    def test_duplicate_configuration_keys_fail_before_subprocess(self):
        path = self.root / 'duplicate.json'; path.write_text('{"status":"READY","status":"FAILED"}')
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_KEY'):
            ci.read_json(path)


if __name__ == '__main__':
    unittest.main()
