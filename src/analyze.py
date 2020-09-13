import requests
import pickle

import nltk.data


def load_transcripts(filename):
    """
    Takes the transcript input file, parse and returns it
    """
    transcripts = []
    with open(filename) as fp:
        transcript_counter, state = 0, 0
        transcript_text = ""
        for line in fp:
            line = line.strip()
            try:
                line_no = int(line)
                if line_no == transcript_counter + 1:
                    # we are starting a new transcript line
                    state = 1
                    if transcript_text:
                        data = {"counter": transcript_counter, "period": transcript_period, \
                                "text": transcript_text, "start": transcript_start_time}
                        transcripts.append(data)
                    transcript_counter = line_no
            except ValueError:
                if state == 1:
                    # get time of this video section in seconds
                    items = line.split(" --> ")[0].split(',')[0].split(':')
                    transcript_start_time = int(items[0])*3600 + int(items[1])*60 + int(items[2])
                    transcript_period = line
                    state += 1
                elif state == 2:
                    # get text
                    transcript_text = line
                    state = 0
        if transcript_text:
            data = {"counter": transcript_counter, "period": transcript_period, \
                    "text": transcript_text, "start": transcript_start_time}
            transcripts.append(data)
    print("Size of transcript: {}".format(len(transcripts)))
    return transcripts


def dedup(text):
    """
    Removes duplicate phrases from spoken transcripts
    """
    tokens = text.split()
    tmp_tokens, clean_tokens = [], []
    # get rid of any dupe bigram
    inx = 0
    while inx < len(tokens) - 1:
        tmp_tokens.append(tokens[inx])
        if tokens[inx] == tokens[inx+1]:
            # we have dupe so skip next
            print("Text: {} --> dupe bigram: {}, inx: {}".format(text, (tokens[inx], tokens[inx+1]), inx))
            inx += 2
        else:
            inx += 1
    if inx <= len(tokens) - 1:
        # add the last unigram
        tmp_tokens.append(tokens[inx])
    inx = 0
    # get rid of any dupe trigram
    while inx < len(tmp_tokens) - 1:
        clean_tokens.append(tmp_tokens[inx])
        if tmp_tokens[inx] == tmp_tokens[inx+1]:
            # we have dupe so skip next
            print("Text: {} --> dupe trigram: {}, inx".format(text, (tmp_tokens[inx], tmp_tokens[inx+1]), inx))
            inx += 2
        else:
            inx += 1
    if inx <= len(tmp_tokens) - 1:
        # add the last unigram
        clean_tokens.append(tmp_tokens[inx])
    clean_text = " ".join(clean_tokens)
    return clean_text


def remove_fillers(text):
    """
    Removes fillers from text
    """
    # Ref: https://en.wikipedia.org/wiki/Filler_(linguistics)
    fillers = set(["um", "er", "uh"])
    tokens = text.split()
    clean_tokens = []
    for token in tokens:
        if token in fillers:
            continue
        clean_tokens.append(token)
    return " ".join(clean_tokens)


def process(transcripts):
    for idx, transcript in enumerate(transcripts):
        dedup_text = dedup(transcript["text"])
        text = remove_fillers(dedup_text)
        if text:
            transcripts[idx]["text"] = text
        else:
            print(text)


def get_punctuation(text):
    # Ref: http://bark.phon.ioc.ee/punctuator#
    url = "http://bark.phon.ioc.ee/punctuator"
    data = {'text': text}
    r = requests.post(url = url, data = data)
    return r.text


def get_unsegmented_text(transcripts):
    unsegmented_text, video_start_times = [], []
    tokens_so_far = 0
    for idx, transcript in enumerate(transcripts):
        text = transcript["text"]
        start_time = str(transcript["start"])  # in second
        time_slot = transcript["period"].split(" --> ")[0]
        video_start_times.append((tokens_so_far, start_time, time_slot))
        unsegmented_text.append(text)
        # get length of this segment in terms of tokens
        tokens_so_far += len(text.split())
    unsegmented_text = " ".join(unsegmented_text)
    return unsegmented_text, video_start_times


def punctuate(unsegmented_text):
    # print(unsegmented_text)
    # get the punctuation
    punctuated_text = get_punctuation(unsegmented_text)
    return punctuated_text


def get_video_slot_times(punctuated_text, video_start_times, tokenizer):
    # segment the text into sentences
    sentences = tokenizer.tokenize(punctuated_text)
    start_times = []
    visited_tokens_so_far = 0
    for sent in sentences:
        tokens_no = len(sent.split())
        print("sent: {}, tokens no: {}".format(sent, tokens_no))
        prev_tokens_so_far, next_tokens_so_far = 0, 0
        for idx, item in enumerate(video_start_times):
            next_tokens_so_far, start_time, time_slot = item
            print("idx: {}, prev_tokens_so_far: {}, next_tokens_so_far: {}, start_time: {}".\
                format(idx, prev_tokens_so_far, next_tokens_so_far, start_time))
            if next_tokens_so_far >= visited_tokens_so_far:
                print("found --> idx: {}, prev_tokens_so_far: {}, next_tokens_so_far: {}, visited_tokens_so_far: {}, start_time: {}".\
                    format(idx, prev_tokens_so_far, next_tokens_so_far, visited_tokens_so_far, start_time))
                break
            prev_tokens_so_far = next_tokens_so_far
        try:
            # check if visited tokens so far is closer to prev_tokens_so_far or next_tokens_so_far
            dist_from_prev = abs(prev_tokens_so_far - visited_tokens_so_far)
            dist_from_next = abs(next_tokens_so_far - visited_tokens_so_far)
            print("sentence: {}".format(sent))
            if dist_from_prev < dist_from_next:
                start_time, time_slot = video_start_times[idx-1][1], video_start_times[idx-1][2]
                print("visited tokens so far: {} is closer to prev_tokens_so_far: {}! start_time: {}".\
                    format(visited_tokens_so_far, prev_tokens_so_far, start_time))
            else:
                start_time, time_slot = item[1], item[2]
                print("visited tokens so far: {} is closer to next_tokens_so_far: {}! start_time: {}".\
                    format(visited_tokens_so_far, next_tokens_so_far, start_time))
            start_times.append((start_time, time_slot))
        except IndexError:
            continue
        visited_tokens_so_far += tokens_no
    return start_times



def generate_html(transcripts, base_url):
    html = ""
    for idx, transcript in enumerate(transcripts):
        start_time = transcript["period"].split(" --> ")[0]
        url = base_url + str(transcript["start"])
        html += '<p><span><a href="' + url + '" target="_blank">[' + start_time + ']</a> – </span>' + transcript["text"] + '</p>\n'
    return html


def generate_html(punctuated_text, start_times, base_url, tokenizer):
    html = ""
    # segment the text into sentences
    sentences = tokenizer.tokenize(punctuated_text)
    trans_inx = 0
    for idx, sentence in enumerate(sentences):
        try:
            start_time, period = start_times[idx]
        except IndexError:
            continue
        url = base_url + start_time
        html += '<p><span><a href="' + url + '" target="_blank">[' + period + ']</a> – </span>' + sentence + '</p>\n'
    return html


def run():
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    filename = "data/peterthiel_you_are_not_a_lottery_ticket_2013_sxsw.srt"
    yt_base_url = "https://youtu.be/iZM_JmZdqCw?t="
    transcripts = load_transcripts(filename)
    # dedupe text & remove fillers
    process(transcripts)
    unsegmented_text, video_start_times = get_unsegmented_text(transcripts)
    # print(video_start_times)
    # punctuated_text = punctuate(transcripts)
    # with open("data/punctuated.txt", "wb") as fp:
    #     pickle.dump(punctuated_text, fp)
    with open('data/punctuated.txt', 'rb') as fp:
        punctuated_text = pickle.load(fp)
    # print(punctuated_text)
    start_times = get_video_slot_times(punctuated_text, video_start_times, tokenizer)
    print(len(start_times))
    print(len(punctuated_text.split('.')))
    html = generate_html(punctuated_text, start_times, yt_base_url, tokenizer)
    # html = generate_html(transcripts, punctuated_text, yt_base_url)
    with open("peter_theil_with_punc.html", "w") as fp:
        fp.write(html)


run()