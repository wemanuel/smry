# Copyright (C) 2003-2007, 2009, 2010 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import struct

import dns.rdtypes.sigbase

class SIG(dns.rdtypes.sigbase.SIGBase):
    """SIG record"""
    def to_digestable(self, origin = None):
        return struct.pack('!HBBIIIH', self.type_covered,
                           self.algorithm, self.labels,
                           self.original_ttl, self.expiration,
                           self.inception, self.key_tag) + \
                           self.signer.to_digestable(origin) + \
                           self.signature
    def _cmp(self, other):
        hs = struct.pack('!HBBIIIH', self.type_covered,
                         self.algorithm, self.labels,
                         self.original_ttl, self.expiration,
                         self.inception, self.key_tag)
        ho = struct.pack('!HBBIIIH', other.type_covered,
                         other.algorithm, other.labels,
                         other.original_ttl, other.expiration,
                         other.inception, other.key_tag)
        v = cmp(hs, ho)
        if v == 0:
            v = cmp(self.signer, other.signer)
            if v == 0:
                v = cmp(self.signature, other.signature)
        return v
