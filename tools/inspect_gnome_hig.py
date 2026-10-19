"""Read current official GNOME guidance from a runner with documentation access."""
from html.parser import HTMLParser
import urllib.request


class Article(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {'main', 'article'}:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in {'main', 'article'}:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth > 0 and data.strip():
            self.parts.append(data.strip())


def main():
    for title, url in [
        ('Header Bars', 'https://developer.gnome.org/hig/patterns/containers/header-bars.html'),
        ('Adaptive Design', 'https://developer.gnome.org/hig/guidelines/adaptive.html'),
    ]:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                document = response.read().decode('utf-8')
            parser = Article()
            parser.feed(document)
            text = '\n'.join(parser.parts)
            if not text:
                raise ValueError('No article text found')
            excerpt = text[:6500].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::notice title=GNOME HIG {title}::{url}%0A{excerpt}', flush=True)
        except Exception as error:
            print(f'::warning title=GNOME HIG {title}::{type(error).__name__}: {error}', flush=True)


if __name__ == '__main__':
    main()
