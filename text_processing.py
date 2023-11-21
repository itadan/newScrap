import datetime
import json
import logging
import requests
import codecs
import asyncio
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from nltk.corpus import stopwords
import pymorphy2
import nltk
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,
    PER,
    NamesExtractor,
    Doc,
)


def insert_value(value: str, dct: dict):
    if value in dct.keys():
        dct[value] += 1
    else:
        dct[value] = 1


async def get_key_definitions(parsed_page: BeautifulSoup, def_dict: dict):
    all_tags = parsed_page.find_all("a", class_="tm-tags-list__link")
    for tag in all_tags:
        text = tag.text
        insert_value(value=text, dct=def_dict)


async def get_content(parsed_page: BeautifulSoup):
    all_text = parsed_page.find(
        "div",
        class_="article-formatted-body article-formatted-body article-formatted-body_version-1",
    )
    for code in all_text.select("code"):
        code.decompose()

    return all_text.get_text().rstrip()


async def get_trendsetters(text_lst: list):
    segmenter = Segmenter()
    morph_vocab = MorphVocab()
    emb = NewsEmbedding()
    morph_tagger = NewsMorphTagger(emb)
    syntax_parser = NewsSyntaxParser(emb)
    ner_tagger = NewsNERTagger(emb)
    names_extractor = NamesExtractor(morph_vocab)

    text = " ".join(text_lst)
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    doc.tag_ner(ner_tagger)

    for span in doc.spans:
        span.normalize(morph_vocab)
    for span in doc.spans:
        if span.type == PER:
            span.extract_fact(names_extractor)
    freq_dict = {}
    for _ in doc.spans:
        if _.fact:
            insert_value(value=_.normal, dct=freq_dict)
    return {key: val for key, val in freq_dict.items() if val != 1 and len(key) != 1}


async def build_wordcloud(text_lst: list):
    nltk.download("stopwords")
    stop_words = stopwords.words("russian")
    stop_words.extend(["это", "также", "всё", "весь", "который", "мочь"])

    text = " ".join(text_lst)

    from nltk.tokenize import word_tokenize

    nltk.download("punkt")
    text = word_tokenize(text)
    lemmatizer = pymorphy2.MorphAnalyzer()

    def lemmatize_text(tokens):
        text_new = ""
        for word in tokens:
            word = lemmatizer.parse(word)
            text_new = text_new + " " + word[0].normal_form
        return text_new

    text = lemmatize_text(text)
    cloud = WordCloud(width=1000, height=1000, stopwords=stop_words).generate(text)

    plt.imshow(cloud)
    plt.show()

    plt.axis("off")


async def dump_def_key_ts_data(def_dict: dict, authors_dict: dict):
    date = str(datetime.datetime.now())
    fixed_dict = {}
    for tag in def_dict.keys():
        if def_dict[tag] != 1:
            fixed_dict[tag] = def_dict[tag]

    json_format = {
        "source": "habr.com",
        "date": date,
        "tags": [
            {"id": id, "tag": key, "frequency": value}
            for id, (key, value) in enumerate(fixed_dict.items())
        ],
        "trendsetters": [
            {"id": id, "Name": key, "frequency": value}
            for id, (key, value) in enumerate(authors_dict.items())
        ],
    }
    with open("static/result_text_processing.json", "w", encoding="utf-8") as fp:
        json.dump(json_format, fp, ensure_ascii=False)
    pass


async def main():
    with codecs.open("static/result.json", encoding="utf-8", mode="r") as f:
        json_data = json.load(f)

    json_data = json_data["articles"]
    urls = [x["href"] for x in json_data]
    tags_dict = {}
    text = []

    for url in urls:
        try:
            req = requests.get(url)
            if req.status_code == 200:
                soup = BeautifulSoup(req.text, "html.parser")
                await get_key_definitions(parsed_page=soup, def_dict=tags_dict)
                text.append(await get_content(parsed_page=soup))

        except Exception as e:
            logging.info("could not save data")
            logging.exception("Exception")

    ts_dict = await get_trendsetters(text_lst=text)
    try:
        await dump_def_key_ts_data(def_dict=tags_dict, authors_dict=ts_dict)
    except Exception as e:
        logging.info("could not dump data")
        logging.exception("Exception")

    try:
        await build_wordcloud(text)
    except Exception as e:
        logging.info("could not build word cloud")
        logging.exception("Exception")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        filename="debug/debug.log",
        filemode="w",
        format="%(asctime)s - %(message)s",
    )
    asyncio.run(main())
