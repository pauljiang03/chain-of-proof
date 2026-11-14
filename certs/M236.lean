import ChainOfProof
open ChainOfProof

namespace Cert.M236

def cited : List Fact := [
  ⟨696, .sessionEvent, 1427040014519541, 1, 298, 0⟩,
  ⟨697, .sessionEvent, 1427131437609200, 1, 302, 0⟩,
  ⟨698, .sessionEvent, 1427131437624800, 1, 302, 0⟩,
  ⟨699, .sessionEvent, 1427131463645645, 1, 302, 0⟩,
  ⟨700, .sessionEvent, 1427131463661245, 1, 297, 300⟩,
  ⟨701, .sessionEvent, 1427131464000000, 1000000, 302, 0⟩,
  ⟨702, .sessionEvent, 1427131464000000, 1000000, 302, 0⟩,
  ⟨703, .sessionEvent, 1427131464659647, 1, 297, 300⟩,
  ⟨704, .sessionEvent, 1427131464800047, 1, 297, 303⟩,
  ⟨705, .sessionEvent, 1427131464862448, 1, 297, 304⟩,
  ⟨706, .sessionEvent, 1427131464940447, 1, 297, 300⟩,
  ⟨707, .sessionEvent, 1427131465065247, 1, 297, 300⟩,
  ⟨708, .sessionEvent, 1427131466244253, 1, 297, 300⟩,
  ⟨709, .sessionEvent, 1427131468422262, 1, 297, 305⟩,
  ⟨710, .sessionEvent, 1427131481036285, 1, 297, 262⟩,
  ⟨711, .sessionEvent, 1427131481036285, 1, 297, 262⟩,
  ⟨712, .sessionEvent, 1427131481067488, 1, 297, 262⟩,
  ⟨713, .sessionEvent, 1427131481067488, 1, 297, 262⟩,
  ⟨714, .sessionEvent, 1427131481691488, 1, 297, 262⟩,
  ⟨715, .sessionEvent, 1427131493981310, 1, 297, 300⟩,
  ⟨716, .sessionEvent, 1427131547191999, 1, 299, 0⟩,
  ⟨717, .sessionEvent, 1427131547191999, 1, 299, 0⟩,
  ⟨718, .sessionEvent, 1427131594578482, 1, 297, 300⟩,
  ⟨719, .sessionEvent, 1427135767849930, 1, 297, 300⟩,
  ⟨720, .sessionEvent, 1427137695571480, 1, 299, 0⟩,
  ⟨721, .sessionEvent, 1427137695571480, 1, 299, 0⟩,
  ⟨722, .sessionEvent, 1427137695586599, 1, 299, 0⟩,
  ⟨723, .sessionEvent, 1427137695586599, 1, 299, 0⟩,
  ⟨724, .sessionEvent, 1427137726442999, 1, 299, 0⟩,
  ⟨725, .sessionEvent, 1427137726442999, 1, 299, 0⟩,
  ⟨726, .sessionEvent, 1427140822997030, 1, 297, 300⟩,
  ⟨727, .sessionEvent, 1427140845605478, 1, 297, 300⟩,
  ⟨728, .sessionEvent, 1427140861714952, 1, 297, 300⟩,
  ⟨729, .sessionEvent, 1427140862354555, 1, 297, 300⟩,
  ⟨730, .sessionEvent, 1427143894555912, 1, 298, 0⟩,
  ⟨731, .sessionEvent, 1427144569000000, 1000000, 298, 0⟩,
  ⟨732, .sessionEvent, 1427144573551575, 1, 301, 262⟩,
  ⟨733, .sessionEvent, 1427144573801176, 1, 301, 262⟩,
  ⟨734, .sessionEvent, 1427144573816776, 1, 301, 262⟩,
  ⟨735, .sessionEvent, 1427144575000000, 1000000, 298, 0⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 696) (.both (Sets.sessionRecorded 697) (.both (Sets.sessionRecorded 698) (.both (Sets.sessionRecorded 699) (.both (Sets.sessionRecorded 700) (.both (Sets.sessionRecorded 701) (.both (Sets.sessionRecorded 702) (.both (Sets.sessionRecorded 703) (.both (Sets.sessionRecorded 704) (.both (Sets.sessionRecorded 705) (.both (Sets.sessionRecorded 706) (.both (Sets.sessionRecorded 707) (.both (Sets.sessionRecorded 708) (.both (Sets.sessionRecorded 709) (.both (Sets.sessionRecorded 710) (.both (Sets.sessionRecorded 711) (.both (Sets.sessionRecorded 712) (.both (Sets.sessionRecorded 713) (.both (Sets.sessionRecorded 714) (.both (Sets.sessionRecorded 715) (.both (Sets.sessionRecorded 716) (.both (Sets.sessionRecorded 717) (.both (Sets.sessionRecorded 718) (.both (Sets.sessionRecorded 719) (.both (Sets.sessionRecorded 720) (.both (Sets.sessionRecorded 721) (.both (Sets.sessionRecorded 722) (.both (Sets.sessionRecorded 723) (.both (Sets.sessionRecorded 724) (.both (Sets.sessionRecorded 725) (.both (Sets.sessionRecorded 726) (.both (Sets.sessionRecorded 727) (.both (Sets.sessionRecorded 728) (.both (Sets.sessionRecorded 729) (.both (Sets.sessionRecorded 730) (.both (Sets.sessionRecorded 731) (.both (Sets.sessionRecorded 732) (.both (Sets.sessionRecorded 733) (.both (Sets.sessionRecorded 734) (Sets.sessionRecorded 735)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M236

#print axioms Cert.M236.verified
