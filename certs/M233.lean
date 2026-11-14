import ChainOfProof
open ChainOfProof

namespace Cert.M233

def cited : List Fact := [
  ⟨576, .sessionEvent, 1427036019905880, 1, 297, 262⟩,
  ⟨577, .sessionEvent, 1427036020280281, 1, 297, 262⟩,
  ⟨578, .sessionEvent, 1427036408475166, 1, 297, 300⟩,
  ⟨579, .sessionEvent, 1427036408615566, 1, 297, 300⟩,
  ⟨580, .sessionEvent, 1427036418412384, 1, 297, 300⟩,
  ⟨581, .sessionEvent, 1427036673457232, 1, 297, 300⟩,
  ⟨582, .sessionEvent, 1427037157117380, 1, 297, 300⟩,
  ⟨583, .sessionEvent, 1427037192170641, 1, 297, 300⟩,
  ⟨584, .sessionEvent, 1427037192857042, 1, 297, 300⟩,
  ⟨585, .sessionEvent, 1427037361446539, 1, 297, 300⟩,
  ⟨586, .sessionEvent, 1427037530051304, 1, 298, 0⟩,
  ⟨587, .sessionEvent, 1427037532829239, 1, 301, 262⟩,
  ⟨588, .sessionEvent, 1427037532860439, 1, 301, 262⟩,
  ⟨589, .sessionEvent, 1427037532860439, 1, 301, 262⟩,
  ⟨590, .sessionEvent, 1427037533000000, 1000000, 298, 0⟩,
  ⟨591, .sessionEvent, 1427037533078840, 1, 301, 262⟩,
  ⟨592, .sessionEvent, 1427037582515327, 1, 297, 300⟩,
  ⟨593, .sessionEvent, 1427037582967728, 1, 298, 0⟩,
  ⟨594, .sessionEvent, 1427037583000000, 1000000, 298, 0⟩,
  ⟨595, .sessionEvent, 1427037586961336, 1, 298, 0⟩,
  ⟨596, .sessionEvent, 1427037588661737, 1, 298, 0⟩,
  ⟨597, .sessionEvent, 1427037604609200, 1, 302, 0⟩,
  ⟨598, .sessionEvent, 1427037604624800, 1, 302, 0⟩,
  ⟨599, .sessionEvent, 1427037751655058, 1, 297, 300⟩,
  ⟨600, .sessionEvent, 1427037751655058, 1, 302, 0⟩,
  ⟨601, .sessionEvent, 1427037774000000, 1000000, 302, 0⟩,
  ⟨602, .sessionEvent, 1427037774000000, 1000000, 302, 0⟩,
  ⟨603, .sessionEvent, 1427037774493498, 1, 297, 300⟩,
  ⟨604, .sessionEvent, 1427037774649498, 1, 297, 303⟩,
  ⟨605, .sessionEvent, 1427037774758699, 1, 297, 304⟩,
  ⟨606, .sessionEvent, 1427037774821098, 1, 297, 300⟩,
  ⟨607, .sessionEvent, 1427037774899099, 1, 297, 300⟩,
  ⟨608, .sessionEvent, 1427037776427902, 1, 297, 300⟩,
  ⟨609, .sessionEvent, 1427037782059311, 1, 297, 300⟩,
  ⟨610, .sessionEvent, 1427037782714514, 1, 297, 305⟩,
  ⟨611, .sessionEvent, 1427037792589331, 1, 297, 300⟩,
  ⟨612, .sessionEvent, 1427037843773020, 1, 297, 262⟩,
  ⟨613, .sessionEvent, 1427037843773020, 1, 297, 262⟩,
  ⟨614, .sessionEvent, 1427037843835421, 1, 297, 262⟩,
  ⟨615, .sessionEvent, 1427037843835421, 1, 297, 262⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 576) (.both (Sets.sessionRecorded 577) (.both (Sets.sessionRecorded 578) (.both (Sets.sessionRecorded 579) (.both (Sets.sessionRecorded 580) (.both (Sets.sessionRecorded 581) (.both (Sets.sessionRecorded 582) (.both (Sets.sessionRecorded 583) (.both (Sets.sessionRecorded 584) (.both (Sets.sessionRecorded 585) (.both (Sets.sessionRecorded 586) (.both (Sets.sessionRecorded 587) (.both (Sets.sessionRecorded 588) (.both (Sets.sessionRecorded 589) (.both (Sets.sessionRecorded 590) (.both (Sets.sessionRecorded 591) (.both (Sets.sessionRecorded 592) (.both (Sets.sessionRecorded 593) (.both (Sets.sessionRecorded 594) (.both (Sets.sessionRecorded 595) (.both (Sets.sessionRecorded 596) (.both (Sets.sessionRecorded 597) (.both (Sets.sessionRecorded 598) (.both (Sets.sessionRecorded 599) (.both (Sets.sessionRecorded 600) (.both (Sets.sessionRecorded 601) (.both (Sets.sessionRecorded 602) (.both (Sets.sessionRecorded 603) (.both (Sets.sessionRecorded 604) (.both (Sets.sessionRecorded 605) (.both (Sets.sessionRecorded 606) (.both (Sets.sessionRecorded 607) (.both (Sets.sessionRecorded 608) (.both (Sets.sessionRecorded 609) (.both (Sets.sessionRecorded 610) (.both (Sets.sessionRecorded 611) (.both (Sets.sessionRecorded 612) (.both (Sets.sessionRecorded 613) (.both (Sets.sessionRecorded 614) (Sets.sessionRecorded 615)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M233

#print axioms Cert.M233.verified
