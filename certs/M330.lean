import ChainOfProof
open ChainOfProof

namespace Cert.M330

def cited : List Fact := [
  ⟨12570, .fileSeen, 1427294860265705, 1, 963, 15453⟩,
  ⟨12571, .fileSeen, 1427294908789805, 1, 965, 15453⟩,
  ⟨12572, .fileSeen, 1427294908805405, 1, 16101, 1549⟩,
  ⟨12573, .fileSeen, 1427294908805405, 1, 16102, 1549⟩,
  ⟨12574, .fileSeen, 1427294908805405, 1, 16103, 1549⟩,
  ⟨12575, .fileSeen, 1427294908867805, 1, 965, 15453⟩,
  ⟨12576, .fileSeen, 1427294972549005, 1, 16104, 15453⟩,
  ⟨12577, .fileSeen, 1427294972549005, 1, 16105, 15453⟩,
  ⟨12578, .fileSeen, 1427294972564605, 1, 16104, 15453⟩,
  ⟨12579, .fileSeen, 1427294972564605, 1, 16105, 15453⟩,
  ⟨12580, .fileSeen, 1427294972564605, 1, 16106, 15453⟩,
  ⟨12581, .fileSeen, 1427294972736205, 1, 16002, 15453⟩,
  ⟨12582, .fileSeen, 1427295014440605, 1, 16107, 15453⟩,
  ⟨12583, .fileSeen, 1427295015376605, 1, 16107, 15453⟩,
  ⟨12584, .fileSeen, 1427295015376605, 1, 16108, 15453⟩,
  ⟨12585, .fileSeen, 1427295015485805, 1, 16108, 15453⟩,
  ⟨12586, .fileSeen, 1427295015485805, 1, 16109, 15453⟩,
  ⟨12587, .fileSeen, 1427295015579405, 1, 16109, 15453⟩,
  ⟨12588, .fileSeen, 1427295419198205, 1, 15502, 15453⟩,
  ⟨12589, .fileSeen, 1427295419260605, 1, 15501, 15453⟩,
  ⟨12590, .fileSeen, 1427295446545005, 1, 15484, 15453⟩,
  ⟨12591, .fileSeen, 1427295446545005, 1, 15497, 15453⟩,
  ⟨12592, .fileSeen, 1427295447293805, 1, 15891, 15453⟩,
  ⟨12593, .fileSeen, 1427295447293805, 1, 15903, 15453⟩,
  ⟨12594, .fileSeen, 1427295447293805, 1, 16005, 15453⟩,
  ⟨12595, .fileSeen, 1427295447293805, 1, 16006, 15453⟩,
  ⟨12596, .fileSeen, 1427295447293805, 1, 16040, 15453⟩,
  ⟨12597, .fileSeen, 1427295447293805, 1, 16041, 15453⟩,
  ⟨12598, .fileSeen, 1427295447293805, 1, 16037, 15453⟩,
  ⟨12599, .fileSeen, 1427295447293805, 1, 16046, 15453⟩,
  ⟨12600, .fileSeen, 1427295447293805, 1, 16042, 15453⟩,
  ⟨12601, .fileSeen, 1427295447293805, 1, 16043, 15453⟩,
  ⟨12602, .fileSeen, 1427295447293805, 1, 16044, 15453⟩,
  ⟨12603, .fileSeen, 1427295447293805, 1, 16038, 15453⟩,
  ⟨12604, .fileSeen, 1427295447293805, 1, 16039, 15453⟩,
  ⟨12605, .fileSeen, 1427295447293805, 1, 16036, 15453⟩,
  ⟨12606, .fileSeen, 1427295447293805, 1, 15846, 15453⟩,
  ⟨12607, .fileSeen, 1427295447293805, 1, 16104, 15453⟩,
  ⟨12608, .fileSeen, 1427295447293805, 1, 16105, 15453⟩,
  ⟨12609, .fileSeen, 1427295447293805, 1, 16106, 15453⟩ ]

def claim : Claim := .both (Sets.fileRecorded 12570) (.both (Sets.fileRecorded 12571) (.both (Sets.fileRecorded 12572) (.both (Sets.fileRecorded 12573) (.both (Sets.fileRecorded 12574) (.both (Sets.fileRecorded 12575) (.both (Sets.fileRecorded 12576) (.both (Sets.fileRecorded 12577) (.both (Sets.fileRecorded 12578) (.both (Sets.fileRecorded 12579) (.both (Sets.fileRecorded 12580) (.both (Sets.fileRecorded 12581) (.both (Sets.fileRecorded 12582) (.both (Sets.fileRecorded 12583) (.both (Sets.fileRecorded 12584) (.both (Sets.fileRecorded 12585) (.both (Sets.fileRecorded 12586) (.both (Sets.fileRecorded 12587) (.both (Sets.fileRecorded 12588) (.both (Sets.fileRecorded 12589) (.both (Sets.fileRecorded 12590) (.both (Sets.fileRecorded 12591) (.both (Sets.fileRecorded 12592) (.both (Sets.fileRecorded 12593) (.both (Sets.fileRecorded 12594) (.both (Sets.fileRecorded 12595) (.both (Sets.fileRecorded 12596) (.both (Sets.fileRecorded 12597) (.both (Sets.fileRecorded 12598) (.both (Sets.fileRecorded 12599) (.both (Sets.fileRecorded 12600) (.both (Sets.fileRecorded 12601) (.both (Sets.fileRecorded 12602) (.both (Sets.fileRecorded 12603) (.both (Sets.fileRecorded 12604) (.both (Sets.fileRecorded 12605) (.both (Sets.fileRecorded 12606) (.both (Sets.fileRecorded 12607) (.both (Sets.fileRecorded 12608) (Sets.fileRecorded 12609)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M330

#print axioms Cert.M330.verified
