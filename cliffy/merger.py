from deepmerge import Merger

cliffy_merger = Merger([(list, ["append_unique"]), (dict, ["merge"])], ["use_existing"], ["use_existing"])
