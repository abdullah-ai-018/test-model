import fitz

p71 = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(p71)
page = doc[14] # A-101

print(f"page.rect: {page.rect}")
print(f"page.rotation: {page.rotation}")

# Without matrix (default 72 dpi)
pix72 = page.get_pixmap()
print(f"pixmap at 72 dpi: {pix72.width} x {pix72.height} (samples: {len(pix72.samples)})")

# With matrix for 150 dpi (scale = 150/72 = 2.0833)
zoom = 150 / 72.0
mat = fitz.Matrix(zoom, zoom)
pix150 = page.get_pixmap(matrix=mat)
print(f"pixmap at 150 dpi: {pix150.width} x {pix150.height}")

# Notice that get_pixmap by default respects page.rotation:
# Rect was (2592, 1728), with rot 90, the rendered upright image is (1728 * zoom, 2592 * zoom)
# Let's verify coordinate transformation:
# In PyMuPDF, page.get_text_blocks() returns coordinates in unrotated or rotated page rect?
blocks = page.get_text("blocks")
print(f"Sample block rect: {blocks[0][:4]}")

doc.close()
