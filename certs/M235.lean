import ChainOfProof
open ChainOfProof

namespace Cert.M235

def cited : List Fact := [
  ⟨656, .sessionEvent, 1427039752360653, 1, 301, 291⟩,
  ⟨657, .sessionEvent, 1427039752360653, 1, 301, 291⟩,
  ⟨658, .sessionEvent, 1427039752423054, 1, 301, 291⟩,
  ⟨659, .sessionEvent, 1427039757259062, 1, 297, 293⟩,
  ⟨660, .sessionEvent, 1427039757259062, 1, 297, 293⟩,
  ⟨661, .sessionEvent, 1427039757274662, 1, 297, 293⟩,
  ⟨662, .sessionEvent, 1427039757290262, 1, 297, 293⟩,
  ⟨663, .sessionEvent, 1427039757680262, 1, 297, 293⟩,
  ⟨664, .sessionEvent, 1427039805514757, 1, 301, 291⟩,
  ⟨665, .sessionEvent, 1427039805514757, 1, 301, 291⟩,
  ⟨666, .sessionEvent, 1427039818020781, 1, 301, 293⟩,
  ⟨667, .sessionEvent, 1427039818036381, 1, 301, 293⟩,
  ⟨668, .sessionEvent, 1427039818036381, 1, 301, 293⟩,
  ⟨669, .sessionEvent, 1427039818114380, 1, 301, 293⟩,
  ⟨670, .sessionEvent, 1427039822419988, 1, 297, 291⟩,
  ⟨671, .sessionEvent, 1427039822435589, 1, 297, 291⟩,
  ⟨672, .sessionEvent, 1427039822435589, 1, 297, 291⟩,
  ⟨673, .sessionEvent, 1427039822435589, 1, 297, 291⟩,
  ⟨674, .sessionEvent, 1427039822435589, 1, 297, 291⟩,
  ⟨675, .sessionEvent, 1427039822544788, 1, 297, 291⟩,
  ⟨676, .sessionEvent, 1427039861899269, 1, 301, 291⟩,
  ⟨677, .sessionEvent, 1427039861914867, 1, 301, 291⟩,
  ⟨678, .sessionEvent, 1427039861914867, 1, 301, 291⟩,
  ⟨679, .sessionEvent, 1427039861977268, 1, 301, 291⟩,
  ⟨680, .sessionEvent, 1427039874426090, 1, 297, 262⟩,
  ⟨681, .sessionEvent, 1427039874426090, 1, 297, 262⟩,
  ⟨682, .sessionEvent, 1427039875533691, 1, 301, 262⟩,
  ⟨683, .sessionEvent, 1427039875533691, 1, 301, 262⟩,
  ⟨684, .sessionEvent, 1427039876376093, 1, 301, 293⟩,
  ⟨685, .sessionEvent, 1427039906374947, 1, 301, 291⟩,
  ⟨686, .sessionEvent, 1427039906374947, 1, 301, 291⟩,
  ⟨687, .sessionEvent, 1427040006000000, 1000000, 298, 0⟩,
  ⟨688, .sessionEvent, 1427040008000000, 1000000, 298, 0⟩,
  ⟨689, .sessionEvent, 1427040008607128, 1, 301, 262⟩,
  ⟨690, .sessionEvent, 1427040008653929, 1, 301, 262⟩,
  ⟨691, .sessionEvent, 1427040008669529, 1, 301, 262⟩,
  ⟨692, .sessionEvent, 1427040008825529, 1, 301, 262⟩,
  ⟨693, .sessionEvent, 1427040009000000, 1000000, 298, 0⟩,
  ⟨694, .sessionEvent, 1427040009652330, 1, 298, 0⟩,
  ⟨695, .sessionEvent, 1427040012444735, 1, 298, 0⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 656) (.both (Sets.sessionRecorded 657) (.both (Sets.sessionRecorded 658) (.both (Sets.sessionRecorded 659) (.both (Sets.sessionRecorded 660) (.both (Sets.sessionRecorded 661) (.both (Sets.sessionRecorded 662) (.both (Sets.sessionRecorded 663) (.both (Sets.sessionRecorded 664) (.both (Sets.sessionRecorded 665) (.both (Sets.sessionRecorded 666) (.both (Sets.sessionRecorded 667) (.both (Sets.sessionRecorded 668) (.both (Sets.sessionRecorded 669) (.both (Sets.sessionRecorded 670) (.both (Sets.sessionRecorded 671) (.both (Sets.sessionRecorded 672) (.both (Sets.sessionRecorded 673) (.both (Sets.sessionRecorded 674) (.both (Sets.sessionRecorded 675) (.both (Sets.sessionRecorded 676) (.both (Sets.sessionRecorded 677) (.both (Sets.sessionRecorded 678) (.both (Sets.sessionRecorded 679) (.both (Sets.sessionRecorded 680) (.both (Sets.sessionRecorded 681) (.both (Sets.sessionRecorded 682) (.both (Sets.sessionRecorded 683) (.both (Sets.sessionRecorded 684) (.both (Sets.sessionRecorded 685) (.both (Sets.sessionRecorded 686) (.both (Sets.sessionRecorded 687) (.both (Sets.sessionRecorded 688) (.both (Sets.sessionRecorded 689) (.both (Sets.sessionRecorded 690) (.both (Sets.sessionRecorded 691) (.both (Sets.sessionRecorded 692) (.both (Sets.sessionRecorded 693) (.both (Sets.sessionRecorded 694) (Sets.sessionRecorded 695)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M235

#print axioms Cert.M235.verified
