def load_transcripts(filename):
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
    # Ref: https://en.wikipedia.org/wiki/Filler_(linguistics)
    fillers = set(["um", "er", "uh"])
    tokens = text.split()
    clean_tokens = []
    for token in tokens:
        if token in fillers:
            continue
        clean_tokens.append(token)
    return " ".join(clean_tokens)


def cleanup(transcripts):
    for idx, transcript in enumerate(transcripts):
        transcripts[idx]["text"] = dedup(transcript["text"])


def generate_html(transcripts):
    base_url = "https://youtu.be/iZM_JmZdqCw?t="
    html = ""
    for idx, transcript in enumerate(transcripts):
        start = transcript["start"]
        dedup_text = dedup(transcript["text"])
        transcripts[idx]["text"] = remove_fillers(dedup_text)
        text = transcript["text"]
        start_time = transcript["period"].split(" --> ")[0]
        url = base_url + str(start)
        html += '<p><span><a href="' + url + '" target="_blank">[' + start_time + ']</a> – </span>' + text + '</p>\n'
    return html


filename = "data/peterthiel_you_are_not_a_lottery_ticket_2013_sxsw.srt"
transcripts = load_transcripts(filename)
html = generate_html(transcripts)
with open("peter_theil.html", "w") as fp:
    fp.write(html)
