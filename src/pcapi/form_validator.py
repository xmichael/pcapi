from bs4 import BeautifulSoup
# from lxml.html.clean import clean_html, Cleaner
# from lxml import etree
from pcapi import logtool
# from pcapi import config
# from StringIO import StringIO
import html5lib
from html5lib import treebuilders
# from html5lib import treewalkers, serializer
# from html5lib.filters import sanitizer

log = logtool.getLogger("FormValidator", "pcapi")

class Editor(object):
    def __init__(self, content):
        self.content = content
        self.soup = BeautifulSoup(self.content, 'html.parser')
        self.elements = ["text", "textarea", "checkbox", "radio", "select", "image", "audio", "range"]

    def findElements(self):
        elements = []
        for tag in self.soup.findAll("div", {"class": "fieldcontain"}):
            check, elem = self.checkForElements(tag["id"])
            if check:
                log.debug("%s, %s" % (tag["id"], self.get_header(elem, tag["id"])))
                elements.append([tag["id"], self.get_header(elem, tag["id"])])
        return elements

    def checkForElements(self, tag):
        for el in self.elements:
            if el in tag and "-buttons" not in tag:
                return (True, el)
        return (False, None)

    def get_header(self, el_type, el_id):
        cases = {"text": "label", "textarea": "label", "range": "label", "radio": "legend", "checkbox": "legend", "select": "legend", "image": None, "audio": None}
        for tag in self.soup.findAll("div", {"id": el_id}):
            if cases[el_type] != None:
                label = tag.find_all(cases[el_type])[0].findAll(text=True)[0]
            else:
                label = el_type
        return label

    def validate(self, el_type, el_id):
        for tag in self.soup.findAll("div", {"id": el_id}):
            for sibling in tag.next_siblings:
                log.debug(sibling)


class FormValidator:

    def __init__(self, content):
        log.debug("initialize form validator")
        self.content = content
        self.soup = BeautifulSoup(self.content, 'html.parser')
        self.valid_tags = ['html', 'body', 'form', 'div', 'input', 'textarea', 'select', 'option', 'button', 'legend', 'label', 'fieldset']

    def validate(self):
        log.debug("start validating")
        if self.clean_it() and self.check_tags():
            #return self.validate_schema()
            return self.validate_html5()
        else:
            return False

    def clean_it(self):
        for string in self.content.split('\n'):
            if "javascript:" in string:
                log.debug("False because of javascript")
                return False
            elif "onclick" in string:
                log.debug("False because of onclick")
                return False
        #cleaner = Cleaner(style=True, links=False, javascript=True, remove_unknown_tags=False, forms=False)
        #log.debug(cleaner.clean_html(self.content))
        return True

    def validate_html5(self):
        log.debug("validate_html5")
        p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
        html = '<!DOCTYPE html><html><head><title>Page Title</title></head><body>%s</body></html>' % self.content
        dom_tree = p.parse(html)
        if len(p.errors) == 0:
            return True
        else:
            return False

        """walker = treewalkers.getTreeWalker("dom")
        stream = walker(dom_tree)
        s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False)
        output_generator = s.serialize(stream)

        for item in output_generator:
            print item"""

    """def validate_schema(self):
        f = open(config.get("path","schemafile"), "r")
        xmlschema_doc = etree.parse(StringIO(f.read()))
        f.close()
        schema = etree.XMLSchema(xmlschema_doc)
        doc = etree.parse(StringIO(self.content))
        return schema.validate(doc)"""

    def check_tags(self):
        log.debug("checking tags")
        for tag in self.soup.findAll(True):
            if tag.name not in self.valid_tags:
                log.debug("False because of tag name %s" % tag.name)
                return False
            else:
                if self.check_attr(tag) == False:
                    return False
        return True

    def check_attr(self, tag):
        #log.debug("check attr")
        if tag.name == 'form':
            #log.debug(tag.attrs)
            if 'action' in tag.attrs:
                return False

        valid_input_type = ['text', 'checkbox', 'radio', 'submit', 'button', 'range', 'file']
        if tag.name == 'input':
            if tag.get('type') not in valid_input_type:
                log.debug("False because of input type %s" % tag.get('type'))
                return False
        return True
