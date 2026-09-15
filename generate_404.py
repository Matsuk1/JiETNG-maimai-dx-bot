"""Generate the missing-image placeholder through HTML/CSS and Playwright."""
from modules.images.renderer import file_uri, render_template

OUTPUT = './assets/pics/404.png'


def generate_404(output=OUTPUT):
    with render_template('404.html', 600, 800, logo=file_uri('assets/pics/logo.png')) as image:
        image.save(output)


if __name__ == '__main__':
    generate_404()
    print(f'Saved to {OUTPUT}')
