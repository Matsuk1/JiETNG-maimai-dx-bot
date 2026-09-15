"""Generate the missing-image placeholder through HTML/CSS and Playwright."""
from modules.html_renderer import file_uri, render_template

OUTPUT = './assets/pics/404.png'


def generate_404(output=OUTPUT, skin=None):
    with render_template('404.html', 600, 800, skin=skin, logo=file_uri('assets/pics/logo.png')) as image:
        image.save(output)


if __name__ == '__main__':
    generate_404()
    print(f'Saved to {OUTPUT}')
