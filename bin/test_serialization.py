from anthology import Anthology
import lz4.frame
import msgpack
import datetime

t_start = datetime.datetime.now()
ant = Anthology("../data")
t_end = datetime.datetime.now()
print(f"      Loaded in {round((t_end - t_start).total_seconds() * 1000)}ms")

t_start = datetime.datetime.now()
obj = ant.serialize()
with lz4.frame.open(
    "test_serialization.lz4", mode="wb", compression_level=lz4.frame.COMPRESSIONLEVEL_MIN
) as f:
    msgpack.pack(obj, f)
t_end = datetime.datetime.now()

print(f"  Serialized in {round((t_end - t_start).total_seconds() * 1000)}ms")

del ant

t_start = datetime.datetime.now()
with lz4.frame.open("test_serialization.lz4", mode="rb") as f:
    obj = msgpack.unpack(f)
    ant = Anthology.from_serialized(obj)
t_end = datetime.datetime.now()

print(f"Deserialized in {round((t_end - t_start).total_seconds() * 1000)}ms")
