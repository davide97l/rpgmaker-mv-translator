import json
import sys
import time
from googletrans import Translator  # pip install googletrans==4.0.0rc1
import argparse
import os
from print_neatly import print_neatly
import copy


def translate(file_path, tr, src='it', dst='en', verbose=False, max_retries=5, max_len=55):

    def translate_sentence(text):
        target = text
        translation = tr.translate(target, src=src, dest=dst).text
        if target[0].isalpha() and translation[0].isalpha and not target[0].isupper():
            translation = translation[0].lower() + translation[1:]
        text = translation
        if verbose:
            print(target, '->', translation)
        return text

    anomalies = 0
    translations = 0
    f = open(file_path)
    data = json.load(f)
    f.close()
    num_ids = len([e for e in data["id"] if e is not None])
    i = 0
    for d in data:
        if d is not None:
            print('{}: {}/{}'.format(file_path, i+1, num_ids))
            i += 1
            name_tr = None
            try:
                name_tr = translate_sentence(d['name'])
                translations += 1
            except:
                for _ in range(max_retries):
                    try:
                        time.sleep(1)
                        name_tr = translate_sentence(d['name'])
                        translations += 1
                    except:
                        pass
            if name_tr is None:
                anomalies += 1
                print('Anomaly {}: {}'.format(anomalies, d['name']))
            d['name'] = name_tr

            desc_tr = None
            d['description'].replace('\n', ' ')
            try:
                desc_tr = translate_sentence(d['description'])
                translations += 1
            except:
                for _ in range(max_retries):
                    try:
                        time.sleep(1)
                        desc_tr = translate_sentence(d['description'])
                        translations += 1
                    except:
                        pass
            if desc_tr is None:
                anomalies += 1
                print('Anomaly {}: {}'.format(anomalies, d['description']))
            try:
                text_neat = print_neatly(desc_tr, max_len)
                desc_tr = text_neat[0] + '\n' + text_neat[1]
            except:
                pass
            d['description'] = desc_tr
    return data, translations


# usage: python objects_translator.py --source_lang it --dest_lang en
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input_folder", type=str, default="objects")
    ap.add_argument("-sl", "--source_lang", type=str, default="it")
    ap.add_argument("-dl", "--dest_lang", type=str, default="en")
    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("-nf", "--no_format", action="store_true", default=False)
    ap.add_argument("-ml", "--max_len", type=int, default=55)
    ap.add_argument("-mr", "--max_retries", type=int, default=10)
    args = ap.parse_args()
    dest_folder = args.input_folder + '_' + args.dest_lang
    translations = 0
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    for file in os.listdir(args.input_folder):
        file_path = os.path.join(args.input_folder, file)
        print('translating file: {}'.format(file_path))
        if file.endswith('.json'):
            if args.print_neatly:
                new_data, t = translate(file_path, tr=Translator(), max_len=args.max_len,
                                        src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                        max_retries=args.max_retries)
            translations += t
            new_file = os.path.join(dest_folder, file)
            with open(new_file, 'w') as f:
                if not args.no_format:
                    json.dump(new_data, f, indent=4)
                else:
                    json.dump(new_data, f)
    print('\ndone! translated in total {} strings'.format(translations))