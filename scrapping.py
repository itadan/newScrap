from bs4 import BeautifulSoup
import requests
import json
import datetime
import logging
import asyncio


async def parse_page(url: str) -> dict:
    article_dict = {}
    req = requests.get(url)
    if req.status_code == 200:
        soup = BeautifulSoup(req.text, "html.parser")
        all_articles = soup.find_all("h2", class_="tm-title tm-title_h2")

        for article in all_articles:  # проходимся по статьям
            article_name = article.a.span.text  # собираем названия статей
            article_link = f'https://habr.com{article.a["href"]}'  # ссылки на статьи
            article_dict[article_name] = article_link

    return article_dict


async def dump_data(dict: dict) -> None:
    date = str(datetime.datetime.now())
    json_format = {
        "source": "habr.com",
        "date": date,
        "articles": [
            {"id": id, "title": key, "href": value}
            for id, (key, value) in enumerate(dict.items())
        ],
    }
    with open("/static/result.json", "w", encoding="utf-8") as fp:
        json.dump(json_format, fp, ensure_ascii=False)


async def main():
    article_dict = {}
    for i in range(5):
        url = f"https://habr.com/ru/search/page{i+1}/?q=%D0%B1%D0%BB%D0%BE%D0%BA%D1%87%D0%B5%D0%B9%D0%BD&target_type=posts&order=relevance"
        try:
            parsed_data = await parse_page(url=url)
            article_dict.update(parsed_data)
        except Exception as e:
            logging.info(f"could not parse {url}, shutting down")
            logging.exception("Exception")
            break
    if article_dict != {}:
        try:
            await dump_data(dict=article_dict)
        except Exception as e:
            logging.info("could not save data")
            logging.exception("Exception")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        filename="debug/debug.log",
        filemode="w",
        format="%(asctime)s - %(message)s",
    )
    asyncio.run(main())
