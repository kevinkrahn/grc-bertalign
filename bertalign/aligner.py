import numpy as np
from bertalign.corelib import *
from bertalign.utils import *

class Bertalign:
    def __init__(self,
                 src,
                 tgt,
                 encoder,
                 max_align=5,
                 top_k=3,
                 win=5,
                 skip=-0.1,
                 margin=True,
                 len_penalty=True,
               ):

        self.max_align = max_align
        self.top_k = top_k
        self.win = win
        self.skip = skip
        self.margin = margin
        self.len_penalty = len_penalty

        if isinstance(src, str):
            src = clean_text(src)
            src_sents = src.splitlines()
        else:
            src_sents = src

        if isinstance(src, str):
            tgt = clean_text(tgt)
            tgt_sents = tgt.splitlines()
        else:
            tgt_sents = tgt

        src_num = len(src_sents)
        tgt_num = len(tgt_sents)

        print("Embedding source text...")
        src_vecs, src_lens = encoder.transform(src_sents, max_align - 1)
        print("Embedding target text...")
        tgt_vecs, tgt_lens = encoder.transform(tgt_sents, max_align - 1)

        char_ratio = np.sum(src_lens[0,]) / np.sum(tgt_lens[0,])

        self.src_sents = src_sents
        self.tgt_sents = tgt_sents
        self.src_num = src_num
        self.tgt_num = tgt_num
        self.src_lens = src_lens
        self.tgt_lens = tgt_lens
        self.char_ratio = char_ratio
        self.src_vecs = src_vecs
        self.tgt_vecs = tgt_vecs

    def align_sents(self):

        print("Performing first-step alignment...")
        D, I = find_top_k_sents(self.src_vecs[0,:], self.tgt_vecs[0,:], k=self.top_k)
        first_alignment_types = get_alignment_types(2) # 0-1, 1-0, 1-1
        first_w, first_path = find_first_search_path(self.src_num, self.tgt_num)
        first_pointers = first_pass_align(self.src_num, self.tgt_num, first_w, first_path, first_alignment_types, D, I)
        first_alignment = first_back_track(self.src_num, self.tgt_num, first_pointers, first_path, first_alignment_types)

        print("Performing second-step alignment...")
        second_alignment_types = get_alignment_types(self.max_align)
        second_w, second_path = find_second_search_path(first_alignment, self.win, self.src_num, self.tgt_num)
        second_pointers = second_pass_align(self.src_vecs, self.tgt_vecs, self.src_lens, self.tgt_lens,
                                            second_w, second_path, second_alignment_types,
                                            self.char_ratio, self.skip, margin=self.margin, len_penalty=self.len_penalty)
        second_alignment = second_back_track(self.src_num, self.tgt_num, second_pointers, second_path, second_alignment_types)
        self.confidence = compute_alignment_confidence(self.src_vecs, self.tgt_vecs, self.src_lens, self.tgt_lens, second_alignment, self.char_ratio)

        print("Finished! Successfully aligned {} source sentences to {} target sentences\n".format(self.src_num, self.tgt_num))
        print("Alignment confidence: {}".format(self.confidence))
        self.result = second_alignment

    def print_sents(self):
        for src_line, tgt_line in self.pairs():
            print(src_line + "\n" + tgt_line + "\n")

    def pairs(self, include_blank=True, src_sents=None, tgt_sents=None):
        if src_sents is None:
            src_sents = self.src_sents
        if tgt_sents is None:
            tgt_sents = self.tgt_sents

        if include_blank == True:
            for bead in self.result:
                src_line = self._get_line(bead[0], src_sents)
                tgt_line = self._get_line(bead[1], tgt_sents)
                yield src_line, tgt_line
        else:
            for bead in self.result:
                src_line = self._get_line(bead[0], src_sents)
                tgt_line = self._get_line(bead[1], tgt_sents)
                if src_line != '' and tgt_line != '':
                    yield src_line, tgt_line

    @staticmethod
    def _get_line(bead, lines):
        line = ''
        if len(bead) > 0:
            line = ' '.join(lines[bead[0]:bead[-1]+1])
        return line
