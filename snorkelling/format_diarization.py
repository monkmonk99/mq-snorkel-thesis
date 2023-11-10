def format_diarization(rev_ai_transcript):
    """
    Formats the diarization of a transcript from the Rev.ai API.

    Parameters
    ----------
    rev_ai_transcript : dict
        Transcript from Rev.ai API.

    Returns
    -------
    diarization : list
        List of dictionaries containing the speaker, start time, end time, and text of each segment.
    """
    diarization = []
    for segment in rev_ai_transcript['monologues']:
        speaker = segment['speaker']
        start_time = None 
        end_time = None
        for element in segment['elements']:
            if start_time is None and element.get('ts') is not None:
                start_time = element['ts']
            if element.get('end_ts') is not None:
                end_time = element['end_ts']
        text = ''.join([element['value'] for element in segment['elements']])
        diarization.append({'speaker': speaker, 'start_time': start_time, 'end_time': end_time, 'text': text})
    return diarization

if __name__ == "__main__":
    import sys
    sys.path.append('./')
    import json
    from mongo_class import Mongo
    config = json.load(open('config.json'))
    with Mongo(db_name='videos', collection_name='diarization') as diarizations:
        obj = list(diarizations.collection.find(limit=100))[50]
        print(format_diarization(obj['diarization']))
        pass
    
    pass