import argparse
import copy
import json
import os
import sys
import time

from googletrans import Translator  # pip install googletrans==4.0.0rc1

from print_neatly import print_neatly


def translate(file_path, tr, src='it', dst='en', verbose=False, max_retries=5):

    def translate_sentence(text):
        target = text
        translation = tr.translate(target, src=src, dest=dst).text
        if target[0].isalpha() and translation[0].isalpha and not target[0].isupper():
            translation = translation[0].lower() + translation[1:]
        text = translation
        if verbose:
            print(target, '->', translation)
        return text

    def try_translate_sentence(text):
        try:
            return (translate_sentence(text), True)
        except:
            for _ in range(max_retries):
                try:
                    time.sleep(1)
                    return (translate_sentence(text), True)
                except:
                    pass
            return (text, False)

    translations = 0
    with open(file_path, 'r', encoding='utf-8-sig') as datafile:
        data = json.load(datafile)
    num_events = len([e for e in data["events"] if e is not None])
    i = 0
    for events in data["events"]:
        if events is not None:
            print('{}: {}/{}'.format(file_path, i+1, num_events))
            i += 1
            for pages in events['pages']:
                for list in pages['list']:

                    # Plain text (ex: ["plain text"])
                    if list['code'] == 401:
                        # null or empty string check
                        if not list['parameters'][0]:
                            continue
                        # translate
                        list['parameters'][0], success = try_translate_sentence(list['parameters'][0])
                        if not success:
                            print('Anomaly plain text: {}'.format(list['parameters'][0]))
                        else:
                            translations += 1

                    # Choices (ex: [["yes", "no"], 1, 0, 2, 0])
                    elif list['code'] == 102:
                        # null or empty list check
                        if not list['parameters'][0]:
                            continue
                        # translate list
                        for j, choice in enumerate(list['parameters'][0]):
                            # null or empty string check
                            if not choice:
                                continue
                            # translate
                            list['parameters'][0][j], success = try_translate_sentence(choice)
                            if not success:
                                print('Anomaly choices: {}'.format(choice))
                            else:
                                translations += 1

                    # Choices (answer) (ex: [0, "yes"])
                    elif list['code'] == 402:
                        # invalid length null or empty string check
                        if len(list['parameters']) != 2 or not list['parameters'][1]:
                            print('Anomaly choices (answer) - Unexpected 402 Code: {}'.format(list['parameters']))
                            continue
                        # translate
                        list['parameters'][1], success = try_translate_sentence(list['parameters'][1])
                        if not success:
                            print('Anomaly choices (answer): {}'.format(list['parameters'][1]))
                        else:
                            translations += 1
    return data, translations


def translate_neatly(file_path, tr, src='it', dst='en', verbose=False, max_len=40, max_retries=5):

    def translate_sentence(text):
        target = text
        translation = tr.translate(target, src=src, dest=dst).text
        if target[0].isalpha() and translation[0].isalpha and not target[0].isupper():
            translation = translation[0].lower() + translation[1:]
        text = translation
        return text

    def try_translate_sentence(text):
        try:
            return (translate_sentence(text), True)
        except:
            for _ in range(max_retries):
                try:
                    time.sleep(1)
                    return (translate_sentence(text), True)
                except:
                    pass
            return (text, False)

    translations = 0
    with open(file_path, 'r', encoding='utf-8-sig') as datafile:
        data = json.load(datafile)
    num_events = len([e for e in data["events"] if e is not None])
    i = 0
    for events in data["events"]:
        if events is not None:
            print('{}: {}/{}'.format(file_path, i+1, num_events))
            i += 1
            for pages in events['pages']:
                len_list = len(pages['list'])
                list_it = 0
                while list_it < len_list:
                    # 102 Choices (dont nestly translate) (ex: [["yes", "no"], 1, 0, 2, 0])
                    if pages['list'][list_it]['code'] == 102:
                        # null or empty list check
                        if not pages['list'][list_it]['parameters'][0]:
                            list_it += 1
                            continue
                        # translate list
                        for j, choice in enumerate(pages['list'][list_it]['parameters'][0]):
                            # null or empty string check
                            if not choice:
                                print('Anomaly choices - Unexpected 102 code: {}'.format(choice))
                                continue
                            # translate
                            pages['list'][list_it]['parameters'][0][j], success = try_translate_sentence(choice)
                            if not success:
                                print('Anomaly choices: {}'.format(choice))
                            else:
                                translations += 1
                        list_it += 1

                    # 402 Choices (answer) (dont nestly translate) (ex: [0, "yes"])
                    elif pages['list'][list_it]['code'] == 402:
                        # invalid length null or empty string check
                        if len(pages['list'][list_it]['parameters']) != 2 or not pages['list'][list_it]['parameters'][1]:
                            print('Anomaly choices (answer) - Unexpected 402 Code: {}'.format(pages['list'][list_it]['parameters']))
                            list_it += 1
                            continue
                        # translate
                        pages['list'][list_it]['parameters'][1], success = try_translate_sentence(pages['list'][list_it]['parameters'][1])
                        if not success:
                            print('Anomaly choices (answer): {}'.format(pages['list'][list_it]['parameters'][1]))
                        else:
                            translations += 1
                        list_it += 1

                    # 401 Plain text (to nestly translate) (ex: ["plain text"])
                    elif pages['list'][list_it]['code'] == 401:
                        list_it_2 = list_it + 1
                        text = copy.deepcopy(pages['list'][list_it]['parameters'])
                        while pages['list'][list_it_2]['code'] == 401:
                            text.append(pages['list'][list_it_2]['parameters'][0])
                            list_it_2 += 1
                        text = ' '.join(text)
                        # empty string check
                        if not text:
                            list_it = list_it_2
                            continue
                        # translate
                        text_tr, success = try_translate_sentence(text)
                        if (not success) or (text_tr is None):
                            print('Anomaly: {}'.format(text))
                        else:
                            try:
                                text_neat = print_neatly(text_tr, max_len)
                            except:
                                text_neat = text_tr
                            for text_it, j in enumerate(range(list_it, list_it_2)):
                                translations += 1
                                if text_it >= len(text_neat):  # translated text is one row shorter
                                    text_neat.append("")
                                if verbose:
                                    print(pages['list'][j]['parameters'][0], "->", text_neat[text_it])
                                pages['list'][j]['parameters'][0] = text_neat[text_it]
                        list_it = list_it_2
                    else:
                        list_it += 1
    return data, translations


def translate_neatly_common_events(file_path, tr, src='it', dst='en', verbose=False, max_len=55, max_retries=5):

    def translate_sentence(text):
        target = text
        translation = tr.translate(target, src=src, dest=dst).text
        if target[0].isalpha() and translation[0].isalpha and not target[0].isupper():
            translation = translation[0].lower() + translation[1:]
        text = translation
        return text

    translations = 0
    with open(file_path, 'r', encoding='utf-8-sig') as datafile:
        data = json.load(datafile)
    num_ids = len([e for e in data if e is not None])
    i = 0
    for d in data:
        if d is not None:
            print('{}: {}/{}'.format(file_path, i+1, num_ids))
            i += 1
            list_it = 0
            len_list = len(d['list'])
            while list_it < len_list:
                if 'code' in d['list'][list_it].keys() and d['list'][list_it]['code'] == 401:
                    list_it_2 = list_it + 1
                    text = copy.deepcopy(d['list'][list_it]['parameters'])
                    while 'code' in d['list'][list_it].keys() and d['list'][list_it_2]['code'] == 401:
                        text.append(d['list'][list_it_2]['parameters'][0])
                        list_it_2 += 1
                    text = ' '.join(text)
                    # empty string check
                    if not text:
                        list_it = list_it_2
                        continue
                    text_tr = None
                    try:
                        text_tr = translate_sentence(text)
                    except:
                        for _ in range(max_retries):
                            try:
                                time.sleep(1)
                                text_tr = translate_sentence(text)
                            except:
                                pass
                            if text_tr is not None:
                                break
                    if text_tr is None:
                        print('Anomaly: {}'.format(text))
                    else:
                        try:
                            text_neat = print_neatly(text_tr, max_len)
                        except:
                            text_neat = text_tr
                        for text_it, j in enumerate(range(list_it, list_it_2)):
                            translations += 1
                            if text_it >= len(text_neat):
                                text_neat.append("")
                            if verbose:
                                print(d['list'][j]['parameters'][0], "->", text_neat[text_it])
                            d['list'][j]['parameters'][0] = text_neat[text_it]
                    list_it = list_it_2
                else:
                    list_it += 1
    return data, translations


# usage: python dialogs_translator.py --print_neatly --source_lang it --dest_lang en
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, default="dialogs")
    ap.add_argument("-sl", "--source_lang", type=str, default="it")
    ap.add_argument("-dl", "--dest_lang", type=str, default="en")
    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("-nf", "--no_format", action="store_true", default=False)
    ap.add_argument("-pn", "--print_neatly", action="store_true", default=False)
    ap.add_argument("-ml", "--max_len", type=int, default=44)
    ap.add_argument("-mr", "--max_retries", type=int, default=10)
    args = ap.parse_args()
    dest_folder = args.input_folder + '_' + args.dest_lang
    translations = 0
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    for file in os.listdir(args.input_folder):
        file_path = os.path.join(args.input_folder, file)
        if os.path.isfile(os.path.join(dest_folder, file)):
            print('skipped file {} because it has already been translated'.format(file_path))
            continue
        if file.endswith('.json'):
            print('translating file: {}'.format(file_path))
            if file.startswith('Map'):
                if args.print_neatly:
                    new_data, t = translate_neatly(file_path, tr=Translator(), max_len=args.max_len,
                                                   src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                                   max_retries=args.max_retries)
                else:
                    new_data, t = translate(file_path, tr=Translator(),
                                            src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                            max_retries=args.max_retries)
            elif file.startswith('CommonEvents'):
                new_data, t = translate_neatly_common_events(file_path, tr=Translator(), max_len=args.max_len,
                                               src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                               max_retries=args.max_retries)
            translations += t
            new_file = os.path.join(dest_folder, file)
            with open(new_file, 'w', encoding='utf-8') as f:
                if not args.no_format:
                    json.dump(new_data, f, indent=4, ensure_ascii=False)
                else:
                    json.dump(new_data, f, ensure_ascii=False)
    print('\ndone! translated in total {} dialog windows'.format(translations))
