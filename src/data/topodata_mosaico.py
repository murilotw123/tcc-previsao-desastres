import rasterio
from rasterio.merge import merge
import glob

arquivos = glob.glob("arquivos/*.tif")
datasets = [rasterio.open(f) for f in arquivos]


mosaico, transform = merge(datasets)


with rasterio.open("declividade_sudeste.tif", "w",
                   driver="GTiff",
                   height=mosaico.shape[1],
                   width=mosaico.shape[2],
                   count=1,
                   dtype=mosaico.dtype,
                   crs=datasets[0].crs,
                   transform=transform) as dest:
    dest.write(mosaico)