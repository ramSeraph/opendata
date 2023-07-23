#import fiona
#import fiona.crs
import osr
import ogr
import glob

from pathlib import Path
import zipfile

def unzip_file(zip_filename):
    target_dir = Path(zip_filename).parent
    print(f'unzipping {zip_filename} to {target_dir}')
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    extracted_dir = zip_filename.replace('.zip', '/')
    return extracted_dir


#TODO: needs to be fixed.. projections seem wrong
def convert_shp_to_geojson(unzipped_folder, out_filename):
    filenames = glob.glob(str(Path(unzipped_folder).joinpath('*.shp')))
    assert len(filenames) == 1, f'{list(filenames)}'
    shp_file = filenames[0]
    #prj_file = shp_file.replace('.shp', '.prj')

    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataset = driver.Open(shp_file)
    layer = dataset.GetLayer()
    spatialRef = layer.GetSpatialRef()
    print(str(spatialRef))

    in_geom_type = None
    for feature in layer:
        geom = feature.GetGeometryRef()
        geom_type = geom.GetGeometryType()
        if in_geom_type == None:
            in_geom_type = geom_type
        elif geom_type != in_geom_type:
            raise Exception(f'found more than one geom types {in_geom_type}, {geom_type}')
    layer.ResetReading()

    out_filename = 'test.geojson'
    outDriver = ogr.GetDriverByName('GeoJSON')
    if Path(out_filename).exists():
        outDriver.DeleteDataSource(out_filename)

    outDataSource = outDriver.CreateDataSource(out_filename)
    outLayer = outDataSource.CreateLayer(out_filename, geom_type=in_geom_type)
    featureDefn = outLayer.GetLayerDefn()
    outFeature.SetGeometry(poly)
    outLayer.CreateFeature(outFeature)


    #with open(prj_file, 'r') as f:
    #    prj_text = f.read()
    #srs = osr.SpatialReference()
    #if srs.ImportFromWkt(prj_text):
    #    raise ValueError(f"Error importing PRJ information from: {prj_file}")
    #srs.AutoIdentifyEPSG()
    #print(str(srs))

    #with fiona.open(shp_file, 'r', crs=fiona.crs.from_epsg(4326)) as source:
    #    #with fiona.open(out_filename, 'w',
    #    #                driver='GeoJSON',
    #    #                crs=fiona.crs.from_epsg(4326),
    #    #                schema=source.schema) as sink:
    #    print(source.crs)
    #    for rec in source:
    #        print(rec)
    #        break

unzipped_folder = 'data/raw/OSM_SHEET_INDEX/' 
#raw_filename = 'data/raw/OSM_SHEET_INDEX.zip'
filename = 'data/index.geojson'
#unzipped_folder = unzip_file(raw_filename)
convert_shp_to_geojson(unzipped_folder, filename)
