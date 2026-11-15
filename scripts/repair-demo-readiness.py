"""Repair local demo profiles and preset templates through their tested lifecycle."""
import argparse
import importlib.util
import json
import pathlib


def repair(environment, fixtures):
    api = environment.API()
    agents = {agent['deviceCode']: agent['agentId']
              for agent in api('/device-agents?page=1&size=100')['content']}
    devices = api('/devices?page=1&size=100')['content']
    configured = {device['deviceCode']: device for device in environment.load(fixtures / 'devices.json')}
    evidence = {'recordedAt': environment.stamp(), 'capabilities': [], 'templates': []}
    for device in devices:
        code = device['deviceCode']
        definition = configured.get(code) or configured.get(code.removesuffix('_B'))
        if definition is None or code not in agents:
            continue
        if device.get('simulatedDeviceType') != definition['simulatedDeviceType']:
            raise RuntimeError(code + ' simulated type differs from its fixture')
        expected = {cap['capabilityType']: cap for cap in definition['capabilities']}
        path = '/devices/' + code + '/capabilities'
        profiles = api(path)
        by_type = {cap['capabilityType']: cap for cap in profiles}
        for capability_type, definition in expected.items():
            profile = by_type.get(capability_type)
            if profile is None:
                profile = api(path, 'POST', definition)
            endpoint = path + '/' + profile['capabilityCode']
            if profile['capabilityStatus'] == 'ENABLED':
                continue
            tested = api(endpoint + '/test', 'POST')
            if tested['capabilityStatus'] != 'TESTED_PASSED':
                raise RuntimeError(code + '/' + capability_type + ' actual capability test failed')
            api(endpoint + '/status', 'POST', {'status': 'ENABLED'})
            evidence['capabilities'].append({'deviceCode': code, 'capabilityType': capability_type,
                                             'status': 'ENABLED'})
    for fixture in environment.load(fixtures / 'baselines.json'):
        matches = [template for template in api('/baseline-templates')
                   if template['isPreset'] and template['templateIntent'] == fixture['taskFamily']]
        if len(matches) != 1:
            raise RuntimeError('Expected one preset for ' + fixture['taskFamily'])
        template = matches[0]
        path = '/baseline-templates/' + str(template['id'])
        # Update only a differing preset. Re-running retains a successfully enabled version.
        body = {'inputParams': [dict(field, range=field.get('range')) for field in fixture['inputParams']],
                'steps': [dict(step, stepSeq=index + 1) for index, step in enumerate(fixture['steps'])]}
        if any(template.get(key) != value for key, value in body.items()):
            template = api(path, 'PUT', body)
        if template['templateStatus'] != 'ENABLED':
            trial = environment.run_baseline(api, template, fixture, agents)
            if trial['result'] != 'SUCCESS':
                raise RuntimeError(fixture['taskFamily'] + ' actual baseline dry run failed')
            api(path + '/enable', 'POST')
        evidence['templates'].append({'taskFamily': fixture['taskFamily'], 'id': template['id'],
                                      'version': template['templateVersion'], 'status': 'ENABLED'})
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1],
                        help='Local workspace holding user.md and local-test-environment.py')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('local_environment', args.workspace / 'scripts/local-test-environment.py')
    environment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(environment)
    fixtures = pathlib.Path(__file__).resolve().parent / 'test-fixtures'
    print(json.dumps(repair(environment, fixtures), ensure_ascii=False, indent=2))
