import re
import urllib.request
from bs4 import BeautifulSoup
from src.config import url_prompt, FILE_INPUT, FILE_OUTPUT, FILE_NOT_FOUND_WORD


class PromptTranslator:
    def _get_word_from_prompt(self, word):
        data = {}
        data["en"] = word
        root = self._get_root(word)
        self._add_simple_word(root, data)
        self._add_meanings(root, data)
        return data

    @staticmethod
    def _is_valid_data(data):
        return data["simple"] != "" and len(data["meanings"]) > 0

    @staticmethod
    def _get_root(word):
        """
        получить данные из url
        """
        url = url_prompt + word

        with urllib.request.urlopen(url) as f:
            html_string = f.read().decode("utf8")
        return BeautifulSoup(html_string, "lxml")

    @staticmethod
    def _add_simple_word(root, data: dict):
        """
        простой перевод
        """
        data["simple"] = root.find_all(id="tText")[0].getText()

    def _add_meanings(self, root, data: dict):
        """
        значения
        """
        meanings = []
        elements = root.find_all(attrs={"class": "cforms_result"})
        for element in elements:
            meanings.append(self._get_word_mean(element))
        data["meanings"] = meanings
        return data

    def _get_word_mean(self, root):
        """
        одно значение слова
        """
        result = {}
        result["en_word"] = self._search_value(root, {"class": "source_only sayWord"})
        result["trans"] = self._search_value(root, {"class": "transcription"})
        result["part"] = self._search_value(root, {"class": "ref_psp"})
        result["other"] = self._search_value(root, {"class": "otherImportantForms"})
        result["items"] = []
        elements = root.find_all(attrs={"class": "translation-item"})
        for element in elements:
            result["items"].append(self._get_one_mean(element))
        return result

    @staticmethod
    def _search_value(root, attr):
        res = root.find_all(attrs=attr)
        if res:
            res = res[0].getText()
            res = re.sub("[\t\n\r]", "", res)
            res = re.sub("[ ]{2,}", " ", res)
            res = res.strip()
        else:
            res = ""
        return res

    def _get_one_mean(self, root):
        result = {}
        result["rus"] = self._search_value(root, {"class": "result_only sayWord"})
        result["ex"] = []
        elements = root.find_all(attrs={"class": "samplesList"})
        for element in elements:
            result["ex"].append(self._get_example(element))
        return result

    def _get_example(self, root):
        res = {}
        res["en"] = self._search_value(root, {"class": "samSource"})
        res["rus"] = self._search_value(root, {"class": "samTranslation"})
        return res

    def make_record(self):
        words = self._get_words()
        with open(FILE_OUTPUT, "w+", encoding="utf-8") as file_out:
            with open(FILE_NOT_FOUND_WORD, "w+", encoding="utf-8") as file_not_found:
                for word in words:
                    print(word)
                    data = self._get_word_from_prompt(word)
                    if self._is_valid_data(data):
                        record = self._make_record(data)
                        file_out.write(record)
                        file_out.write("\n")
                    else:
                        print("---don't find ", word)
                        file_not_found.write(word)

    @staticmethod
    def _get_words():
        words = []
        with open(FILE_INPUT, "r", encoding='utf-8') as f:
            for line in f:
                line = line.replace(",", "").strip()
                if line:
                    words.append(line)
        return words

    def _make_record(self, data):
        word = data["en"]
        soup = BeautifulSoup("", "html.parser")
        word_en = soup.new_tag("div", **{"class": "en_simple"})
        word_en.string = word

        word_rus = soup.new_tag("div", **{"class": "rus_simple"})
        word_rus.string = data["simple"]

        word_mean = self._make_mean_for_anki(data)

        result = ";".join([str(word_en), str(word_rus), str(word_mean)])
        return result

    @staticmethod
    def _make_mean_for_anki(data):
        soup = BeautifulSoup("", "html.parser")
        for mean in data["meanings"]:
            tag_mean = soup.new_tag("div", **{"class": "mean"})
            en_word = soup.new_tag("span", **{"class": "en_word"})
            en_word.string = mean["en_word"]
            tag_mean.append(en_word)

            trans = soup.new_tag("span", **{"class": "trans"})
            trans.string = mean["trans"]
            tag_mean.append(trans)

            part = soup.new_tag("span", **{"class": "part"})
            part.string = mean["part"]
            tag_mean.append(part)
            soup.append(tag_mean)

            other = soup.new_tag("div", **{"class": "other"})
            other.string = mean["other"]
            tag_mean.append(other)

            for item in mean["items"]:
                item_rus = soup.new_tag("div", **{"class": "item_rus"})
                item_rus.string = item["rus"]
                tag_mean.append(item_rus)

                for example in item["ex"]:
                    ext = soup.new_tag("div", **{"class": "ex"})
                    ex_en = soup.new_tag("span", **{"class": "ex_en"})
                    ex_en.string = example["en"]
                    ext.append(ex_en)

                    ex_rus = soup.new_tag("span", **{"class": "ex_rus"})
                    ex_rus.string = example["rus"]
                    ext.append(ex_rus)

                    tag_mean.append(ext)
        return soup
