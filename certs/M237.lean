import ChainOfProof
open ChainOfProof

namespace Cert.M237

def cited : List Fact := [
  ⟨736, .sessionEvent, 1427144575236378, 1, 301, 262⟩,
  ⟨737, .sessionEvent, 1427144579900787, 1, 298, 0⟩,
  ⟨738, .sessionEvent, 1427144581000000, 1000000, 298, 0⟩,
  ⟨739, .sessionEvent, 1427144581959990, 1, 298, 0⟩,
  ⟨740, .sessionEvent, 1427144592490009, 1, 298, 0⟩,
  ⟨741, .sessionEvent, 1427203265624800, 1, 302, 0⟩,
  ⟨742, .sessionEvent, 1427203265656000, 1, 302, 0⟩,
  ⟨743, .sessionEvent, 1427203289399240, 1, 297, 300⟩,
  ⟨744, .sessionEvent, 1427203289399240, 1, 302, 0⟩,
  ⟨745, .sessionEvent, 1427203296000000, 1000000, 302, 0⟩,
  ⟨746, .sessionEvent, 1427203296000000, 1000000, 302, 0⟩,
  ⟨747, .sessionEvent, 1427203296481653, 1, 297, 300⟩,
  ⟨748, .sessionEvent, 1427203296653254, 1, 297, 303⟩,
  ⟨749, .sessionEvent, 1427203296715654, 1, 297, 304⟩,
  ⟨750, .sessionEvent, 1427203296824854, 1, 297, 300⟩,
  ⟨751, .sessionEvent, 1427203296902853, 1, 297, 300⟩,
  ⟨752, .sessionEvent, 1427203297949461, 1, 297, 300⟩,
  ⟨753, .sessionEvent, 1427203298835484, 1, 297, 305⟩,
  ⟨754, .sessionEvent, 1427203304983509, 1, 297, 262⟩,
  ⟨755, .sessionEvent, 1427203304983509, 1, 297, 262⟩,
  ⟨756, .sessionEvent, 1427203305045908, 1, 297, 262⟩,
  ⟨757, .sessionEvent, 1427203305045908, 1, 297, 262⟩,
  ⟨758, .sessionEvent, 1427203305560709, 1, 297, 262⟩,
  ⟨759, .sessionEvent, 1427203317353931, 1, 297, 300⟩,
  ⟨760, .sessionEvent, 1427203420220510, 1, 297, 300⟩,
  ⟨761, .sessionEvent, 1427210070786434, 1, 297, 300⟩,
  ⟨762, .sessionEvent, 1427210498226231, 1, 297, 300⟩,
  ⟨763, .sessionEvent, 1427210498507030, 1, 297, 300⟩,
  ⟨764, .sessionEvent, 1427210559911482, 1, 297, 300⟩,
  ⟨765, .sessionEvent, 1427211974466702, 1, 297, 300⟩,
  ⟨766, .sessionEvent, 1427221718261791, 1, 301, 262⟩,
  ⟨767, .sessionEvent, 1427221718261791, 1, 301, 262⟩,
  ⟨768, .sessionEvent, 1427221718261791, 1, 297, 262⟩,
  ⟨769, .sessionEvent, 1427221718261791, 1, 297, 262⟩,
  ⟨770, .sessionEvent, 1427230732193810, 1, 297, 300⟩,
  ⟨771, .sessionEvent, 1427231243000000, 1000000, 298, 0⟩,
  ⟨772, .sessionEvent, 1427231245000000, 1000000, 298, 0⟩,
  ⟨773, .sessionEvent, 1427231245488918, 1, 301, 262⟩,
  ⟨774, .sessionEvent, 1427231245566917, 1, 301, 262⟩,
  ⟨775, .sessionEvent, 1427231245566917, 1, 301, 262⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 736) (.both (Sets.sessionRecorded 737) (.both (Sets.sessionRecorded 738) (.both (Sets.sessionRecorded 739) (.both (Sets.sessionRecorded 740) (.both (Sets.sessionRecorded 741) (.both (Sets.sessionRecorded 742) (.both (Sets.sessionRecorded 743) (.both (Sets.sessionRecorded 744) (.both (Sets.sessionRecorded 745) (.both (Sets.sessionRecorded 746) (.both (Sets.sessionRecorded 747) (.both (Sets.sessionRecorded 748) (.both (Sets.sessionRecorded 749) (.both (Sets.sessionRecorded 750) (.both (Sets.sessionRecorded 751) (.both (Sets.sessionRecorded 752) (.both (Sets.sessionRecorded 753) (.both (Sets.sessionRecorded 754) (.both (Sets.sessionRecorded 755) (.both (Sets.sessionRecorded 756) (.both (Sets.sessionRecorded 757) (.both (Sets.sessionRecorded 758) (.both (Sets.sessionRecorded 759) (.both (Sets.sessionRecorded 760) (.both (Sets.sessionRecorded 761) (.both (Sets.sessionRecorded 762) (.both (Sets.sessionRecorded 763) (.both (Sets.sessionRecorded 764) (.both (Sets.sessionRecorded 765) (.both (Sets.sessionRecorded 766) (.both (Sets.sessionRecorded 767) (.both (Sets.sessionRecorded 768) (.both (Sets.sessionRecorded 769) (.both (Sets.sessionRecorded 770) (.both (Sets.sessionRecorded 771) (.both (Sets.sessionRecorded 772) (.both (Sets.sessionRecorded 773) (.both (Sets.sessionRecorded 774) (Sets.sessionRecorded 775)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M237

#print axioms Cert.M237.verified
