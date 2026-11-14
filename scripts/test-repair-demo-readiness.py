import copy
import importlib.util
import pathlib
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('repair_demo', ROOT / 'repair-demo-readiness.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DemoRepairTest(unittest.TestCase):
    def environment(self, test_passes=True, trial_passes=True):
        fixture = {'taskFamily': 'SPECIAL_PASSENGER_SERVICE', 'inputParams': [],
                   'steps': [{'capabilityType': 'CAP_INFO_DISPLAY'}]}
        template = {'id': 2, 'isPreset': True, 'templateIntent': fixture['taskFamily'],
                    'templateVersion': 'V1.13', 'templateStatus': 'ENABLED', 'inputParams': [], 'steps': []}
        profile = {'capabilityCode': 'DISPLAY', 'capabilityType': 'CAP_INFO_DISPLAY',
                   'capabilityStatus': 'UNTESTED'}
        calls = []

        def api(path, method='GET', data=None):
            calls.append((path, method))
            if path.startswith('/device-agents'):
                return {'content': [{'deviceCode': 'SIM_F2_DISPLAY_B', 'agentId': 'A-2'}]}
            if path.startswith('/devices?'):
                return {'content': [{'deviceCode': 'SIM_F2_DISPLAY_B', 'simulatedDeviceType': 'SMART_DISPLAY'}]}
            if path.endswith('/capabilities'):
                return [profile]
            if path.endswith('/test'):
                return dict(profile, capabilityStatus='TESTED_PASSED' if test_passes else 'TESTED_FAILED')
            if path.endswith('/status'):
                profile['capabilityStatus'] = data['status']
                return profile
            if path == '/baseline-templates':
                return [copy.deepcopy(template)]
            if method == 'PUT':
                template.update(data, templateStatus='DRAFT', templateVersion='V1.14')
                return copy.deepcopy(template)
            if path.endswith('/enable'):
                template['templateStatus'] = 'ENABLED'
                return template
            raise AssertionError(path)

        def load(path):
            if path.name == 'baselines.json':
                return [fixture]
            return [{'deviceCode': 'SIM_F2_DISPLAY', 'simulatedDeviceType': 'SMART_DISPLAY',
                     'capabilities': [profile]}]

        env = types.SimpleNamespace(API=lambda: api, load=load, stamp=lambda: 'test',
                                    run_baseline=lambda *args: {'result': 'SUCCESS' if trial_passes else 'FAILED'})
        return env, calls

    def test_repairs_backup_and_missing_channel_then_reruns_without_new_template_version(self):
        env, calls = self.environment()
        result = module.repair(env, ROOT)
        self.assertEqual('SIM_F2_DISPLAY_B', result['capabilities'][0]['deviceCode'])
        self.assertEqual('V1.14', result['templates'][0]['version'])
        calls.clear()
        module.repair(env, ROOT)
        self.assertFalse(any(method != 'GET' for _, method in calls))

    def test_failed_capability_test_never_enables_profile_or_changes_template(self):
        env, calls = self.environment(test_passes=False)
        with self.assertRaises(RuntimeError):
            module.repair(env, ROOT)
        self.assertFalse(any(path.endswith('/status') or method == 'PUT' for path, method in calls))

    def test_failed_dry_run_never_enables_template(self):
        env, calls = self.environment(trial_passes=False)
        with self.assertRaises(RuntimeError):
            module.repair(env, ROOT)
        self.assertFalse(any(path.endswith('/enable') for path, _ in calls))


if __name__ == '__main__':
    unittest.main()
