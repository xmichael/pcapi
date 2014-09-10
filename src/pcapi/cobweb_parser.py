import html5lib, re, json, os
from bs4 import BeautifulSoup

class COBWEBFormParser:

    def __init__(self, content):
        self.content = content

    def extract(self):
        return json.dumps(self._get_dict_from_html())

    def _get_dict_from_html(self):
        if self.content:
            soup = BeautifulSoup(self.content, "html5lib")
            finds = soup.find_all('div', attrs={'class': 'fieldcontain'})
            return {"type": "auth", "graph": self._get_elements(finds)}
        else:
            return None

    def _get_elements(self, tags):
        els = []
        for tag in tags:
            if tag.find('legend'):
                els.append(self._get_group_elements(tag))
            else:
                els.append(self._get_element(tag))
        return els

    def _get_element(self, tag):
        if tag.find('input'):
            if 'text' in tag.find('input').attrs['name']:
                return self._get_input_text(tag, multiline=False)
            elif tag.find('input').attrs['type'] == 'file':
                return self._get_button(tag, tag.get('id').split("-")[1])
            elif 'range' in tag.find('input').attrs['name']:
                return self._get_slider(tag)
        elif tag.find('textarea'):
            return self._get_input_text(tag, multiline=True)

    def _get_group_elements(self, tag):
        if tag.find('input'):
            values = []
            for sub in tag.find_all('input'):
                values.append(sub.attrs['value'])
            return self._get_group(tag, 'select', values)
        elif tag.find('select'):
            values = []
            for sub in tag.find_all('option'):
                values.append(sub.attrs['value'])
            return self._get_group(tag, 'select', values)

    def _get_input_text(self, tag, multiline):
        element = self._get_simple_input(tag, 'text', 'String', tag.find('label').getText())
        element["properties"] = {"multiline":multiline}
        element["children"] = {}
        return element

    def _get_slider(self, tag):
        return self._get_simple_input(tag, 'slider', 'integer', tag.find('label').getText())

    def _get_button(self, tag, t):
        return self._get_simple_input(tag, t, '', tag.find('label').getText())

    def _get_group(self, tag, sel_type, values):
        element = self._get_simple_input(tag, 'list', sel_type, tag.find('legend').getText())
        element['values'] = values
        return element

    def _get_simple_input(self, tag, itype, vtype, q):
        element = {}
        element["input_type"] = itype
        element["value_type"] = vtype
        element["question"] = q
        element["field-id"] = tag.get('id')
        element["id"] = tag.get('id').split("-")[2]
        element["children"] = {}
        return element

if __name__ == "__main__":
    f = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'test', 'resources', 'sample.html')
    with open(f, 'rb') as f:
        parser = COBWEBFormParser(f)
        print parser.extract()