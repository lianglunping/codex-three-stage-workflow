"""Exercise model compatibility without granting stage or write authority."""
import csv
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT.parent / 'staged-agent-run-protocol/scripts'))
from validate_workflow_contract import resolve_case, detect_invocation_mode, validate_content, REFERENCE_FILES
from validate_parallel_coordination_contract import resolve
from sar_utils import validate_model_for_role

POLICY = json.loads((Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'policies/three-stage-runtime-v1.json').read_text())['model_roles']
CASES = json.loads((ROOT / 'references/regression_cases.json').read_text(encoding='utf-8'))
CORE_MODELS = ('gpt-6.1-sol', 'gpt-5.6-sol', 'gpt-6-astra')


class ModelCompatibility(unittest.TestCase):
    def test_unknown_runtime_does_not_select_policy_first_model(self):
        row=next(r for r in CASES if r['expected_stage']=='EXECUTE' and r['expected_transition']=='EXECUTE')
        for policy in (POLICY, dict(reversed(list(POLICY.items())))):
            self.assertEqual(resolve_case(row,policy,None)[3],'PAUSE_CURRENT_MODEL_UNKNOWN')
            for model in CORE_MODELS:
                self.assertEqual(resolve_case(row,policy,model)[5],model)

    def test_all_routing_cases_preserve_compatible_models(self):
        fields = ('expected_route', 'expected_stage', 'expected_autonomy_mode',
                  'expected_transition', 'expected_specialist', 'expected_model',
                  'expected_model_role')
        for model in CORE_MODELS:
            for row in CASES:
                with self.subTest(model=model, case=row['case_id']):
                    expected = tuple(model if field == 'expected_model' and
                                     row[field] == 'gpt-6.1-sol' else row[field]
                                     for field in fields)
                    self.assertEqual(resolve_case(row,POLICY,model),expected)

    def test_ui_prompt_preserves_manual_default_and_maintenance_intent(self):
        ui=(ROOT/'agents/openai.yaml').read_text()
        prompt=next(line.split(':',1)[1].strip().strip('"') for line in ui.splitlines() if 'default_prompt:' in line)
        self.assertEqual(detect_invocation_mode(prompt,'implementation_planning'),'MANUAL')
        self.assertEqual(detect_invocation_mode('自动完成3阶段工作流','workflow_maintenance'),'NONE')

    def test_missing_core_boundary_or_reference_is_detected(self):
        core=(ROOT/'SKILL.md').read_text()
        agents=(Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'AGENTS.md').read_text()
        ui=(ROOT/'agents/openai.yaml').read_text()
        refs={name:(ROOT/'references'/name).read_text() for name in REFERENCE_FILES}
        self.assertEqual(validate_content(core,agents,ui,refs),[])
        for token in ('【执行方案】','Never install globally.','references/state-contract.md'):
            self.assertTrue(validate_content(core.replace(token,''),agents,ui,refs))

    def test_registered_roles_and_exact_model_id_rejection(self):
        for role in ('READ_ONLY_REVIEWER','AUDITOR','STAGING_WRITER','CANONICAL_INTEGRATOR'):
            for model in CORE_MODELS:
                self.assertTrue(validate_model_for_role(model,role))
            for model in ('unknown-model', 'gpt-6.1-sol-unknown', 'sol'):
                self.assertFalse(validate_model_for_role(model,role))
        self.assertFalse(validate_model_for_role('gpt-5.6-luna','CANONICAL_INTEGRATOR'))

    def test_current_model_preserved_and_incompatible_model_pauses(self):
        row=next(r for r in CASES if r['expected_stage']=='EXECUTE' and r['expected_transition']=='EXECUTE')
        for model in (*CORE_MODELS, 'gpt-5.6-terra'):
            self.assertEqual(resolve_case(row,POLICY,model)[5],model)
        for model in ('gpt-5.6-luna','unknown-model'):
            result=resolve_case(row,POLICY,model)
            self.assertEqual(result[3],'PAUSE_MODEL_ROLE_UNAVAILABLE')
            self.assertEqual(result[5],'unavailable')

    def test_missing_approval_cannot_become_execute(self):
        row=next(r.copy() for r in CASES if r['expected_stage']=='EXECUTE' and r['autonomy_mode']=='MANUAL')
        row.update(prior_stage='REFINE',approval_evidence='none')
        for model in CORE_MODELS:
            self.assertEqual(resolve_case(row,POLICY,model)[1],'REFINE')

    def test_write_scope_stage_and_root_boundaries(self):
        row=dict(case_id='compatible_root',stage='EXECUTE',model='gpt-6.1-sol',agent_path='/root',
                 role='CANONICAL_INTEGRATOR',base_matches='true',write_scope='CANONICAL',
                 overlaps_active='false',active_work='false',active_writer_count='0',
                 observations_match='true',drift_class='none',receipt_present='true',receipt_current='true')
        for model in CORE_MODELS:
            row['model'] = model
            self.assertEqual(resolve(row,POLICY),'ALLOW_CANONICAL_EXECUTION')
            for changes,expected in [({'agent_path':'/root/child'},'REJECT_NONROOT_INTEGRATOR'),
                                 ({'stage':'ANALYZE'},'REJECT_PLANNING_WRITE_ROLE'),
                                 ({'stage':'REFINE'},'REJECT_PLANNING_WRITE_ROLE'),
                                 ({'active_writer_count':'1'},'REJECT_SECOND_ACTIVE_WRITER'),
                                 ({'role':'AUDITOR'},'REJECT_READONLY_WRITE'),
                                 ({'role':'STAGING_WRITER'},'REJECT_STAGING_SCOPE'),
                                 ({'base_matches':'false'},'REJECT_STALE_BASE')]:
                with self.subTest(model=model, changes=changes):
                    self.assertEqual(resolve({**row,**changes},POLICY),expected)


if __name__=='__main__':
    unittest.main()
