import argparse
import copy
import json
import os
import sys
import time
import os  # Added for environment variable access

import google.generativeai as genai # Replaced googletrans
# from googletrans import Translator # pip install googletrans==4.0.0rc1 # Removed googletrans

from print_neatly import print_neatly


def translate(file_path, model, src='it', dst='en', verbose=False, max_retries=5): # Removed tr, added model

    def translate_sentence(text_to_translate): # Renamed text to text_to_translate to avoid conflict
        target = text_to_translate
        # translation = tr.translate(target, src=src, dest=dst).text # Old googletrans call
        prompt = f"Translate the following text from {src} to {dst}: {target}"
        try:
            response = model.generate_content(prompt)
            translation = response.text
        except Exception as e:
            print(f"Error during Gemini API call: {e}")
            # It's important to decide how to handle API errors.
            # For now, returning original text and False like try_translate_sentence
            return target, False # Or raise the exception

        if target and translation and target[0].isalpha() and translation[0].isalpha() and not target[0].isupper():
            translation = translation[0].lower() + translation[1:]
        # text = translation # Not needed, directly return translation
        if verbose:
            print(target, '->', translation)
        return translation, True # Return success status

    def try_translate_sentence(text_to_translate): # Renamed text
        try:
            # translate_sentence now returns a tuple (translated_text, success_boolean)
            return translate_sentence(text_to_translate)
        except Exception as e_outer: # Catch potential errors from the API call itself if not handled inside translate_sentence
            print(f"Outer exception in try_translate_sentence: {e_outer}")
            for i in range(max_retries):
                try:
                    time.sleep(1)
                    # translate_sentence now returns a tuple (translated_text, success_boolean)
                    return translate_sentence(text_to_translate)
                except Exception as e_inner: # Catch potential errors from the API call itself
                    print(f"Inner exception in try_translate_sentence on retry {i+1}: {e_inner}")
                    pass
            return (text_to_translate, False)

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
                                # list['parameters'][0] was already updated by try_translate_sentence if successful

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
                                # list['parameters'][0][j] was already updated

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
                                # list['parameters'][1] was already updated
    return data, translations


def translate_neatly(file_path, model, src='it', dst='en', verbose=False, max_len=40, max_retries=5): # Removed tr, added model

    def translate_sentence(text_to_translate): # Renamed text
        target = text_to_translate
        # translation = tr.translate(target, src=src, dest=dst).text # Old googletrans call
        prompt = f"Translate the following text from {src} to {dst}: {target}"
        try:
            response = model.generate_content(prompt)
            translation = response.text
        except Exception as e:
            print(f"Error during Gemini API call: {e}")
            return target, False # Return original and failure status

        if target and translation and target[0].isalpha() and translation[0].isalpha() and not target[0].isupper():
            translation = translation[0].lower() + translation[1:]
        # text = translation # Not needed
        # No verbose print here, it's handled in the main loop of translate_neatly
        return translation, True # Return success status

    def try_translate_sentence(text_to_translate): # Renamed text
        try:
            return translate_sentence(text_to_translate)
        except Exception as e_outer:
            print(f"Outer exception in try_translate_sentence: {e_outer}")
            for i in range(max_retries):
                try:
                    time.sleep(1)
                    return translate_sentence(text_to_translate)
                except Exception as e_inner:
                    print(f"Inner exception in try_translate_sentence on retry {i+1}: {e_inner}")
                    pass
            return (text_to_translate, False)

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
                                # pages['list'][list_it]['parameters'][0][j] was updated
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
                                # pages['list'][list_it]['parameters'][1] was updated
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
                        translated_text, success = try_translate_sentence(text) # text_tr renamed
                        if (not success) or (translated_text is None): # text_tr renamed
                            print('Anomaly: {}'.format(text))
                        else:
                            try:
                                text_neat = print_neatly(translated_text, max_len) # text_tr renamed
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


def translate_neatly_common_events(file_path, model, src='it', dst='en', verbose=False, max_len=55, max_retries=5): # tr removed, model added

    # This function has its own translate_sentence, different from the others.
    # It doesn't have a try_translate_sentence helper.
    def translate_sentence_common(text_to_translate): # Renamed text
        target = text_to_translate
        prompt = f"Translate the following text from {src} to {dst}: {target}"
        translation_result = None # Initialize
        try:
            response = model.generate_content(prompt)
            translation_result = response.text
        except Exception as e:
            print(f"Error during Gemini API call in translate_sentence_common: {e}")
            # Attempt retries directly here as there's no try_translate_sentence
            for i in range(max_retries): # max_retries is from the outer scope
                try:
                    time.sleep(1)
                    response = model.generate_content(prompt)
                    translation_result = response.text
                    if translation_result: # Break if successful
                        break
                except Exception as e_inner:
                    print(f"Inner exception in translate_sentence_common on retry {i+1}: {e_inner}")
                    pass
        
        if not translation_result: # If still no translation after retries
            return target, False # Return original and failure

        if target and translation_result and target[0].isalpha() and translation_result[0].isalpha() and not target[0].isupper():
            translation_result = translation_result[0].lower() + translation_result[1:]
        # text = translation_result # Not needed
        # No verbose print here
        return translation_result, True

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
                    
                    # Call the modified translate_sentence_common which now returns (text, success)
                    translated_text, success = translate_sentence_common(text) # text_tr renamed

                    if not success or translated_text is None: # text_tr renamed
                        print('Anomaly: {}'.format(text))
                    else:
                        try:
                            text_neat = print_neatly(translated_text, max_len) # text_tr renamed
                        except:
                            text_neat = [translated_text] # print_neatly expects a string and returns a list. If it fails, wrap in list.
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

    # --- Gemini API Key Configuration ---
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1) # Exit if key is not found
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro') # Initialize the model once
    except Exception as e:
        print(f"Error configuring Gemini API or model: {e}")
        sys.exit(1)
    # --- End Gemini API Key Configuration ---

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
                    new_data, t = translate_neatly(file_path, model=model, max_len=args.max_len, # Pass model
                                                   src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                                   max_retries=args.max_retries)
                else:
                    new_data, t = translate(file_path, model=model, # Pass model
                                            src=args.source_lang, dst=args.dest_lang, verbose=args.verbose,
                                            max_retries=args.max_retries)
            elif file.startswith('CommonEvents'):
                new_data, t = translate_neatly_common_events(file_path, model=model, max_len=args.max_len, # Pass model
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
