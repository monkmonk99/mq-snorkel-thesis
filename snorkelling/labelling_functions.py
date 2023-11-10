from snorkel.labeling import labeling_function
import re
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer

ABSTAIN = -1
CALL = 1
NOTCALL = 0

# This file will contain lists of categories of labelling functions

@labeling_function()
def scambait_in_title_or_desc(x):
    """The word scambait in the title or description means its much more likely to be a scambaiting call"""
    return CALL if "scambait" in x.title.lower() or "scambait" in x.desc.lower() else NOTCALL

@labeling_function()
def scammer_in_title_or_desc(x):
    """The word scammer in the title or description means its much more likely to be a scambaiting call"""
    return CALL if "scammer" in x.title.lower() or "scammer" in x.desc.lower() else ABSTAIN

@labeling_function()
def sponsor_in_video(x):
    """Sponsors pollute videos with less calls"""
    return NOTCALL if "sponsor" in x.desc.lower() else ABSTAIN

@labeling_function()
def small_video(x):
    """Smaller videos likely have less budget"""
    return CALL if x.views < 20000 else ABSTAIN

@labeling_function()
def hacking(x):
    """Videos that include hacking usually correlate with scambaiting"""
    return NOTCALL if "hack" in x.desc.lower() else ABSTAIN

@labeling_function()
def live_stream(x):
    """Live streams are less likely to be scam calls, but often content creators will link to their live streams in the description of their videos"""
    return NOTCALL if "live" in x.title.lower() else ABSTAIN

@labeling_function()
def comments_disabled(x):
    """Comments disabled implies this may be a news snippet"""
    return NOTCALL if len(x.comments) > 0 and x.comments[0] == "<<<Comments Disabled>>>" else ABSTAIN

# added
@labeling_function()
def news_not_in_channel(x):
    """The word news should not be in the channel"""
    return NOTCALL if "news" in x.channel_name.lower() else ABSTAIN

# added
@labeling_function()
def travelling_not_in_title_or_desc(x):
    """The word travelling should not be in the title"""
    return NOTCALL if "travel" in x.title.lower() or "travelling" in x.desc.lower() else ABSTAIN

# General functions array
general = [sponsor_in_video, small_video, hacking, live_stream, comments_disabled, news_not_in_channel, scambait_in_title_or_desc, travelling_not_in_title_or_desc, scammer_in_title_or_desc]

# Scam type

@labeling_function()
def refund_scam(x):
    """Refund scams are conducted over phone calls"""
    return CALL if "refund" in x.desc.lower() or "refund" in x.title.lower() else ABSTAIN

@labeling_function()
def irs_scam(x):
    """IRS scams are conducted over phone calls"""
    return CALL if "irs" in x.desc.lower() or "irs" in x.title.lower() else ABSTAIN

@labeling_function()
def crypto_scam(x):
    """Crypto scams are not conducted over phone calls"""
    return NOTCALL if "crypto" in x.desc.lower() or "crypto" in x.title.lower() else ABSTAIN

@labeling_function()
def not_a_scheme(x):
    """A scheme generally implies a greater complexity than a scam call"""
    return NOTCALL if "scheme" in x.desc.lower() or "scheme" in x.title.lower() else ABSTAIN

# added
@labeling_function()
def tech_support(x):
    """Tech support is a common premise for scams"""
    return CALL if "tech support" in x.desc.lower() or "tech support" in x.title.lower() else ABSTAIN

scam_companies = ["geek squad", "norton", "microsoft"]

@labeling_function()
def common_scam_companies(x):
    """Scam companies are more likely to be scam calls"""
    return CALL if any(company in x.desc.lower() or company in x.title.lower() for company in scam_companies) else ABSTAIN

# Scam type functions array
scam_types = [refund_scam, irs_scam, crypto_scam, not_a_scheme, common_scam_companies, tech_support]


# Transcript functions

@labeling_function()
def two_hellos(x):
    """One greeting can be presumed to be an intro, the second is the hello to a scam call"""
    greetings_count = 0
    if x['transcription'] is not pd.NA:    
        for chunk in x['transcription']:
            greetings_count += len(re.findall(r'\bhello\b', chunk['text'].lower()))
            greetings_count += len(re.findall(r'\bhi\b', chunk['text'].lower()))
            greetings_count += len(re.findall(r'\byo\b', chunk['text'].lower()))
            greetings_count += len(re.findall(r'\bhey\b', chunk['text'].lower()))
    return CALL if greetings_count > 1 else ABSTAIN

# added
@labeling_function()
def thanks_for_calling(x):
    """A scam call will thank the person for calling"""
    if x['transcription'] is pd.NA:
        return ABSTAIN
    return CALL if "thank you for calling" in x['transcription_block'].lower() else ABSTAIN

@labeling_function()
def only_two_people_speaking(x):
    """Looking at each 30 sec block, if there are 2 speakers occupy 85% of the block it is a scam call"""
    if x['transcription'] is pd.NA:
        return ABSTAIN
    majority = 0.70 # define the threshold for majority for a block
    majority_blocks = 0.5 # define the threshold for majority of blocks
    mainly_two_speakers = [] # array of booleans denoting whether each 30s block was mainly two speakers
    speaker_sum_for_block = {} # each integer key denotes the total time spent by each speaker in that block
    total_sum = 0 # sum in seconds of the entire block
    for chunk in x['transcription']:
        if chunk['start_time'] > ((len(mainly_two_speakers) * 30) + 30):
            # find a combination of speakers that occupy 85% of the block
            for speaker in speaker_sum_for_block:
                for speaker2 in speaker_sum_for_block:
                    # it cannot be one speaker occupying the entire block
                    if speaker_sum_for_block[speaker2]/total_sum > majority:
                        mainly_two_speakers.append(0)
                        break
                    elif speaker != speaker2 and (speaker_sum_for_block[speaker] + speaker_sum_for_block[speaker2])/total_sum > majority:
                        mainly_two_speakers.append(1)
                        break
            else:
                mainly_two_speakers.append(0)
            speaker_sum_for_block = {}
            total_sum = 0
        speaker_sum_for_block[chunk['speaker']] = speaker_sum_for_block.get(chunk['speaker'], 0) + (chunk['end_time'] - chunk['start_time'])
        total_sum += (chunk['end_time'] - chunk['start_time'])
    sum_of_blocks = 0 # the count of blocks dominated by two speakers
    for i in mainly_two_speakers:
        sum_of_blocks += i
    return CALL if len(mainly_two_speakers) > 0 and sum_of_blocks/len(mainly_two_speakers) > majority_blocks else ABSTAIN

@labeling_function()
def number_of_speakers(x):
    """Scam calls are generally conducted by two people"""
    if x['transcription'] is pd.NA:
        return ABSTAIN
    speakers = set()
    for chunk in x['transcription']:
        speakers.add(chunk['speaker'])
    return CALL if len(speakers) > 1 and len(speakers) <= 3 else ABSTAIN

@labeling_function()
def transcript_sentiment(x):
    """Scam calls are generally positive"""
    if x['transcription'] is pd.NA:
        return ABSTAIN
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(x['transcription_block'])
    return CALL if sentiment['pos'] > sentiment['neg'] else ABSTAIN

# added
@labeling_function()
def anydesk_in_transcript(x):
    """Anydesk is a common tool used in scam calls"""
    if x['transcription'] is pd.NA:
        return ABSTAIN
    return CALL if "anydesk" in x['transcription_block'].lower() or "any desk" in x["transcription_block"] else ABSTAIN

# added
@labeling_function()
def secure_server_in_transcript(x):
    """Secure server is common jargon used in scam calls"""
    if x['transcription'] is pd.NA:
        return ABSTAIN
    return CALL if "secure server" in x['transcription_block'].lower() or "secure server" in x["transcription_block"] else ABSTAIN

# added 2
@labeling_function()
def pronoun_usage(x):
    """The usage of third person pronouns (they, etc) should not be more than the use of second person pronouns (you, etc)"""
    second_person = re.compile(r'(you|your|yours|yourself|yourselves)')
    third_person = re.compile(r'(he|him|his|she|her|hers|they|them|their|theirs|himself|herself|themselves)')  
    if x['transcription'] is pd.NA:
        return ABSTAIN
    # use x['transcription_block'] as a string
    second_person_matches = re.findall(second_person, x['transcription_block'].lower())
    third_person_matches = re.findall(third_person, x['transcription_block'].lower())
    if len(third_person_matches) == 0 and len(second_person_matches) == 0:
        return ABSTAIN
    return NOTCALL if len(third_person_matches)/(len(third_person_matches) + len(second_person_matches)) > 0.65 else ABSTAIN

transcript = [two_hellos, thanks_for_calling, only_two_people_speaking, transcript_sentiment, anydesk_in_transcript, secure_server_in_transcript, pronoun_usage]

def get_lfs():
    return {
        "general": general,
        "scam_types": scam_types,
        "transcript": transcript
    }

def get_lfs_array():
    return general + scam_types + transcript