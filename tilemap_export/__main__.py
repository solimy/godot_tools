import ctypes
import struct
import argparse
import godot_parser
import pandas as pd
from typing import List


class Tile:
    __slots__ = [
        'x', 'y', 'source_id', 'coord_x', 'coord_y', 'alternative_tile'
    ]

    def __init__(self, seq) -> None:
        #
        # not very clear, that's not the order it should be written according to :
        # https://github.com/godotengine/godot/blob/59d98ed3bb1ed744600e599f997c817f63157d83/scene/2d/tile_map.cpp#L836
        # however that's how it is beeing read if format == 2, which is my case, according to :
        # https://github.com/godotengine/godot/blob/59d98ed3bb1ed744600e599f997c817f63157d83/scene/2d/tile_map.cpp#L869
        #
        (
            self.x,
            self.y,
            self.source_id,
            self.alternative_tile,
            self.coord_x,
            self.coord_y,
        ) = struct.unpack('hhHHHH', seq)

    def __str__(self) -> str:
        return f'x={self.x}, y={self.y}, source_id={self.source_id}, coord_x={self.coord_x}, coord_y={self.coord_y}, alternative_tile={self.alternative_tile}'

    def __repr__(self) -> str:
        return self.__str__()


def parse_tiles(poolIntArray: godot_parser.objects.GDObject) -> List[Tile]:
    tiles = poolIntArray.args
    tiles = map(ctypes.c_uint32, tiles)
    tiles = map(bytes, tiles)
    tiles = b''.join(tiles)
    tiles = struct.unpack('12s' * (len(tiles) // 12), tiles)
    tiles = map(Tile, tiles)
    tiles = list(tiles)
    return tiles


def parse_args():
    parser = argparse.ArgumentParser(description='Godot TileMap exporter')
    parser.add_argument('tscn', type=str, help='Path to the .tscn file')
    parser.add_argument('tilemap', type=str, help='TileMap\'s name')
    parser.add_argument('output', type=str, help='output file')
    return parser.parse_args()


if __name__=='__main__':
    args = parse_args()
    tscn = args.tscn
    tilemap = args.tilemap
    scn = godot_parser.GDScene.load(tscn)
    with scn.use_tree() as tree:
        tilemap = tree.get_node(tilemap)
        tiles = parse_tiles(tilemap.properties['tile_data'])

        tileset_id = tilemap.properties['tile_set'].id
        tileset = scn.find_sub_resource(id=tileset_id)

        tiles_collisions = [int(k.split('/')[0]) for k, v in tileset.properties.items() if 'shapes' in k and v]

        tiles = pd.DataFrame([(tile.x, tile.y, tile.source_id) for tile in tiles], columns=['x', 'y', 'source'])
        tiles.loc[:, 'walkable'] = True
        tiles.loc[tiles.source.isin(tiles_collisions), 'walkable'] = False
        tiles = tiles.drop(columns=['source'])

        tiles.to_csv(args.output, index=False)
