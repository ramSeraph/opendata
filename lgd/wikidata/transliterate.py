import json
import csv
from pathlib import Path
from ai4bharat.transliteration import XlitEngine

class CachedTransliterator:
    def __init__(self):
        self.supported_langs = [ 'te', 'mr', 'ta', 'bn', 'gu', 'hi', 'kn', 'ml', 'pa', 'or', 'ur', 'as', 'ne' ]
        self.transliterator = None
        self.known_translits = {}
        translit_path = Path('data/transliterations.csv')
        if not translit_path.exists():
            return
        with open(translit_path, 'r') as f:
            reader = csv.reader(f)
            for r in reader:
                lcode = r[0]
                if lcode not in self.known_translits:
                    self.known_translits[lcode] = {}
                word = r[1]
                transliteration = r[2]
                self.known_translits[lcode][word] = transliteration

    def _get_transliterator(self):
        if self.transliterator is None:
            self.transliterator = XlitEngine("en", beam_width=4, rescore=True, src_script_type = 'indic')
        return self.transliterator

    def convert_lang_code(self, lcode):
        if lcode == 'new':
            return 'ne'
        if lcode == 'bho':
            return 'hi'
        return lcode

    def transliterate(self, lcode, word):
        lcode = self.convert_lang_code(lcode)
        if lcode not in self.supported_langs:
            raise Exception(f'unsupported language code {lcode=}')
        per_lang = self.known_translits.get(lcode, {})
        if word in per_lang:
            return per_lang[word]

        t = self._get_transliterator()
        out = t.translit_sentence(word, lcode)
        #print(f'{lcode} - "{word}" --> "{out}"') 
        if lcode not in self.known_translits:
            self.known_translits[lcode] = {}
        self.known_translits[lcode][word] = out
        with open('data/transliterations.csv', 'a') as f:
            wr = csv.writer(f)
            wr.writerow([lcode, word, out])
        return out

    def is_lang_supported(self, lcode):
        lcode = self.convert_lang_code(lcode)
        if lcode in self.supported_langs:
            return True
        return False


if __name__ == '__main__':
    import unidecode
    t = CachedTransliterator()
    with open('data/indian_entities.jsonl', 'r') as f:
        for line in f:
            item = json.loads(line)
            v = item['data']
            qid = item['id']
            labels = v.get('labels', {})
            aliases = v.get('labels', {})
            if 'en' in labels:
                continue
    
            en_label = None
            en_aliases = None
            unsup_langs = []
            all_langs = list(labels.keys())
            all_langs = sorted(all_langs)
            for k in all_langs:
                label = labels[k]['value']
                l_aliases = aliases.get(k, [])
                if k in ['vi', 'nl', 'ca', 'ceb', 'it', 'es', 'hif', 'ms', 'de', 'fr', 'pl', 'sv', 'da', 'cs']:
                    en_label = unidecode.unidecode(label)
                    en_aliases = [ unidecode.unidecode(a) for a in l_aliases ] 
                    break
    
                if not t.is_lang_supported(k):
                    unsup_langs.append(k)
                else:
                    en_label = t.transliterate(k, label)
                    en_aliases = [ t.transliterate(k, a) for a in l_aliases ] 
                    #print(f'transilterated {label=} to {en_label=}')
                    break
            if en_label is None:
                #if len(unsup_langs) == 0:
                #    print(qid)
                #print(qid)
                print(f'{qid} - unsupported langs found: {unsup_langs}')

     #with open('data/indian_entities.jsonl', 'r') as f:
     #   for line in f:
     #       item = json.loads(line)
     #       v = item['data']
     #       qid = item['id']
     #       aliases = 


