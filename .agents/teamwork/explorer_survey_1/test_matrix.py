import fitz

doc = fitz.open(r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf')
p = doc[14]
# Check text page vs pixmap
print("MediaBox:", p.mediabox)
print("CropBox:", p.cropbox)
print("Rotation:", p.rotation)
print("Transformation matrix:", p.transformation_matrix)
print("Derotation matrix:", p.derotation_matrix)
doc.close()
