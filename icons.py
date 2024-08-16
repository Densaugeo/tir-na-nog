# Installed pillow (10.3.0)

from PIL import Image

# Green Favicon was a simple color swap of the 32x32 dark favicon from
# den-antares.com
Image.open('favicon-32x32-green.png') \
    .save('static/favicon.ico', sizes=[(32, 32)])
