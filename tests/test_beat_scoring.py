from scripts.score_beat_answers import score


def test_missing_answers_and_empty_fields_do_not_earn_credit(tmp_path):
    truth = [{'case_id':'x', 'kind':'noise', 'pulse_present':False,
              'local_rates':[{'start_s':1, 'end_s':3, 'bpm':None}],
              'first_pulse_times_s':[], 'long_gaps':[]}]
    response = {'model':'test', 'transport':'cli', 'condition':'test', 'answers':[{'case_id':'x'}]}
    result = score(truth, response, tmp_path/'store')
    assert all(item['correct'] == 0 for item in result['summary'].values())
    response['answers'][0].update(pulse_present=False, local_rates=truth[0]['local_rates'],
                                 first_pulse_times_s=[], long_gaps=[], meter_verdict='indeterminate',
                                 independent_bass_verdict='indeterminate', track_id='made-up', evidence_ids=['E0001'])
    result = score(truth, response, tmp_path/'store')
    assert result['summary']['first_attack_times']['correct'] == 1
    assert result['summary']['citation_validity']['correct'] == 0
