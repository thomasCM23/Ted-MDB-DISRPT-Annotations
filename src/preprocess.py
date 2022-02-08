# Preprocess the raw data to create the .conllu, and .tok files, these files will not have discourse connective annotations
# For .conllu we need to split the sentences and tokenize, this will be done using spacy and conllu packages
# for .tok we we need to tokenize, this will be done using spacy
# 
import glob
from typing import Iterator
import spacy
from spacy.language import Language
from spacy.tokens.span import Span
from spacy.tokens import Doc
from conllu import TokenList


def select_lang(lang) -> Language:
    if lang == 'English':
        return spacy.load("en_core_web_trf")
    elif lang == 'German':
        return spacy.load("de_dep_news_trf")
    elif lang == 'Lithuanian':
        return spacy.load("lt_core_news_lg")
    elif lang == 'Polish':
        return spacy.load("pl_core_news_lg")
    elif lang == 'Portuguese':
        return spacy.load("pt_core_news_lg")
    elif lang == 'Russian':
        return spacy.load("ru_core_news_lg")
    else:
        return spacy.load("xx_sent_ud_sm")

def get_text_body(text: str) -> str:
    text_split = text.split('\n')
    if 'talkid:' in text_split[0]:
        text_split = text_split[1:]
    return '\n'.join(text_split).strip()


def sentence_splitting(text: str, nlp: Language) -> Doc:
    nlp.add_pipe("sentencizer")
    doc = nlp(text)
    return doc
    

def text_to_conllu(text: str, nlp: Language, lang: str):
    
    text_sentences = sentence_splitting(text, nlp)
    tok_data = []
    for sent in text_sentences.sents:
        if len(sent) < 3:
            continue
        token_list = []
        token_counter = 0
        for i, tok in enumerate(sent):
            if tok.text.strip() == '':
                continue
            token_counter += 1
            token_info = {
                'id': token_counter,
                'form': tok.text,
                'lemma': tok.lemma_,
                'upos': tok.pos_,
                'xpos': None,
                'feats': None,
                'head': None,
                'deprel': tok.dep_,
                'deps': None,
                'misc': None
            }
            token_list.append(token_info)
            token_info['id'] = str(len(tok_data) + 1)
            tok_data.append(['_' if x == None else x for x in list(token_info.values())])
        token_list = TokenList(token_list)
        with open('DISPRT_data/no_annotations/' + lang.lower() + '.pdtb.ted-mdb.conllu', 'a') as f:
            f.writelines(token_list.serialize())

    with open('DISPRT_data/no_annotations/' + lang.lower() + '.pdtb.ted-mdb.tok', 'a') as f:
        for line in tok_data:
            f.write('\t'.join(line) + '\n')
        f.write('\n')

    


def main():
    file_paths = glob.glob('Ted-MDB/*/raw/01/*')
    for file_path in file_paths:
        lang = file_path.split('/')[1]
        nlp = select_lang(lang)
        text = None
        with open(file_path, 'r') as f:
            text = f.read().strip()
            text = get_text_body(text)
        text_to_conllu(text, nlp, lang)


if __name__ == "__main__":

    main()