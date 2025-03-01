import os
import glob
import json

from pathlib import Path

import mercantile

from pmtiles.reader import MmapSource, Reader as PMTilesReader, all_tiles

class MissingTileError(Exception):
    pass


class DiskSource:
    def __init__(self, directory):
        self.dir = directory

    def get_tile_from_file(self, fname):
        parts = fname.split('/')
        tile = mercantile.Tile(z=int(parts[-3]),
                               x=int(parts[-2]),
                               y=int(parts[-1].replace('.webp', '')))
        return tile

    def file_from_tile(self, tile):
        return f'{self.dir}/{tile.z}/{tile.x}/{tile.y}.webp'

    def get_tile_data(self, tile):
        fname = self.file_from_tile(tile)
        try:
            os.stat(fname)
        except FileNotFoundError:
            raise MissingTileError()

        with open(fname, 'rb') as f:
            return f.read()

    def get_tile_size(self, tile):
        fname = self.file_from_tile(tile)
        try:
            fstats = os.stat(fname)
        except FileNotFoundError:
            raise MissingTileError()
        return fstats.st_size
        
    def for_all_z(self, z):
        fnames = glob.glob(f'{self.dir}/{z}/*/*.webp')
        for fname in fnames:
            tile = self.get_tile_from_file(fname)
            fstats = os.stat(fname)
            yield (tile, fstats.st_size)

    def all(self):
        fnames = glob.glob(f'{self.dir}/*/*/*.webp')
        for fname in fnames:
            tile = self.get_tile_from_file(fname)
            t_data = Path(fname).read_bytes()
            yield (tile, t_data)

    def cleanup(self):
        pass
        
class PartitionedPMTilesSource:
    def __init__(self, pmtiles_prefix, partition_file):
        self.part_prefix = pmtiles_prefix
        # TODO: get partition info from the pmtiles themselves
        with open(partition_file, 'r') as f:
            p_info = json.load(f)
        self.suffix_arr = list(p_info.keys())
        suffix_to_index = { fname:i for i,fname in enumerate(self.suffix_arr) }
        self.tiles_to_suffix = {}
        self.tiles_to_size = {}
        for suffix, data in p_info.items():
            for t_str, size in data['tiles'].items():
                t = t_str.split(',')
                tile = mercantile.Tile(x=int(t[1]), y=int(t[2]), z=int(t[0]))
                self.tiles_to_suffix[tile] = suffix_to_index[suffix]
                self.tiles_to_size[tile] = size

        self.files = []
        self.readers = {}
        for suffix in p_info.keys():
            fname = f'{pmtiles_prefix}{suffix}.pmtiles'
            file = open(fname, 'rb')
            self.files.append(file)
            src = MmapSource(open(fname, 'rb'))
            reader = PMTilesReader(src)
            self.readers[suffix] = reader

    def get_reader_from_tile(self, tile):
        if tile not in self.tiles_to_suffix:
            raise MissingTileError()
        s = self.tiles_to_suffix[tile]
        suffix = self.suffix_arr[s]
        reader = self.readers[suffix]
        return reader


    def get_tile_data(self, tile):
        reader = self.get_reader_from_tile(tile)
        data = reader.get(tile.z, tile.x, tile.y)
        if data is None:
            raise MissingTileError()
        return data

    def get_tile_size(self, tile):
        if tile not in self.tiles_to_size:
            raise MissingTileError()
        return self.tiles_to_size[tile]

    def for_all_z(self, z):
        for tile, size in self.tiles_to_size.items():
            if tile.z == z:
                yield (tile, size)

    def all(self):
        for suffix, reader in self.readers.items():
            print(f'yielding from {suffix}')
            for t, t_data in all_tiles(reader.get_bytes):
                tile = mercantile.Tile(x=t[1], y=t[2], z=t[0])
                yield tile, t_data

    def cleanup(self):
        for f in self.files:
            f.close()

 

class DiskAndPartitionedPMTilesSource:
    def __init__(self, directory, pmtiles_prefix, partition_file):
        self.dsrc = DiskSource(directory)
        self.psrc = PartitionedPMTilesSource(pmtiles_prefix, partition_file)
        
    def get_tile_data(self, tile):
        try:
            return self.dsrc.get_tile_data(tile)
        except MissingTileError:
            return self.psrc.get_tile_data(tile)

    def get_tile_size(self, tile):
        try:
            return self.dsrc.get_tile_size(tile)
        except MissingTileError:
            return self.psrc.get_tile_size(tile)

    def for_all_z(self, z):
        print(f'iterating over all {z}')
        seen = set()
        for (tile, size) in self.dsrc.for_all_z(z):
            seen.add(tile)
            yield (tile, size)

        print(f'iterated over all {z} disk')
        for (tile, size) in self.psrc.for_all_z(z):
            if tile in seen:
                continue
            yield (tile, size)
        print(f'iterated over all {z} pmtiles')

    def all(self):
        print('yielding from disk')
        for res in self.dsrc.all():
            yield res
        print('yielding from pmtiles files')
        for res in self.psrc.all():
            yield res

    def cleanup(self):
        self.dsrc.cleanup()
        self.psrc.cleanup()


