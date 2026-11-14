import ChainOfProof
open ChainOfProof

namespace Cert.M240

def cited : List Fact := [
  ⟨856, .sessionEvent, 1427295438230204, 1, 297, 300⟩,
  ⟨857, .sessionEvent, 1427295438479805, 1, 297, 300⟩,
  ⟨858, .sessionEvent, 1427296734221603, 1, 297, 300⟩,
  ⟨859, .sessionEvent, 1427297455000000, 1000000, 298, 0⟩,
  ⟨860, .sessionEvent, 1427297457775204, 1, 301, 262⟩,
  ⟨861, .sessionEvent, 1427297457900003, 1, 301, 262⟩,
  ⟨862, .sessionEvent, 1427297457915604, 1, 301, 262⟩,
  ⟨863, .sessionEvent, 1427297458000000, 1000000, 298, 0⟩,
  ⟨864, .sessionEvent, 1427297458399204, 1, 301, 262⟩,
  ⟨865, .sessionEvent, 1427297460000000, 1000000, 298, 0⟩,
  ⟨866, .sessionEvent, 1427297460240000, 1, 299, 0⟩,
  ⟨867, .sessionEvent, 1427297460240000, 1, 299, 0⟩,
  ⟨868, .sessionEvent, 1427297460364799, 1, 298, 0⟩,
  ⟨869, .sessionEvent, 1427297465232008, 1, 298, 0⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 856) (.both (Sets.sessionRecorded 857) (.both (Sets.sessionRecorded 858) (.both (Sets.sessionRecorded 859) (.both (Sets.sessionRecorded 860) (.both (Sets.sessionRecorded 861) (.both (Sets.sessionRecorded 862) (.both (Sets.sessionRecorded 863) (.both (Sets.sessionRecorded 864) (.both (Sets.sessionRecorded 865) (.both (Sets.sessionRecorded 866) (.both (Sets.sessionRecorded 867) (.both (Sets.sessionRecorded 868) (Sets.sessionRecorded 869)))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M240

#print axioms Cert.M240.verified
