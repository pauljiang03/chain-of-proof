import ChainOfProof
open ChainOfProof

namespace Cert.M234

def cited : List Fact := [
  ⟨616, .sessionEvent, 1427037844131821, 1, 297, 262⟩,
  ⟨617, .sessionEvent, 1427037904193928, 1, 297, 300⟩,
  ⟨618, .sessionEvent, 1427038106000000, 1000000, 298, 0⟩,
  ⟨619, .sessionEvent, 1427038106119034, 1, 298, 0⟩,
  ⟨620, .sessionEvent, 1427038108000000, 1000000, 298, 0⟩,
  ⟨621, .sessionEvent, 1427038108000000, 1000000, 298, 0⟩,
  ⟨622, .sessionEvent, 1427038108026711, 1, 301, 262⟩,
  ⟨623, .sessionEvent, 1427038108073509, 1, 301, 262⟩,
  ⟨624, .sessionEvent, 1427038108073509, 1, 301, 262⟩,
  ⟨625, .sessionEvent, 1427038108323111, 1, 301, 262⟩,
  ⟨626, .sessionEvent, 1427038108791111, 1, 298, 0⟩,
  ⟨627, .sessionEvent, 1427038112004717, 1, 298, 0⟩,
  ⟨628, .sessionEvent, 1427038113627119, 1, 298, 0⟩,
  ⟨629, .sessionEvent, 1427038997593599, 1, 302, 0⟩,
  ⟨630, .sessionEvent, 1427038997609200, 1, 302, 0⟩,
  ⟨631, .sessionEvent, 1427039016516434, 1, 297, 300⟩,
  ⟨632, .sessionEvent, 1427039016516434, 1, 302, 0⟩,
  ⟨633, .sessionEvent, 1427039017998434, 1, 297, 300⟩,
  ⟨634, .sessionEvent, 1427039018000000, 1000000, 302, 0⟩,
  ⟨635, .sessionEvent, 1427039018000000, 1000000, 302, 0⟩,
  ⟨636, .sessionEvent, 1427039018154436, 1, 297, 303⟩,
  ⟨637, .sessionEvent, 1427039018279236, 1, 297, 304⟩,
  ⟨638, .sessionEvent, 1427039018388435, 1, 297, 300⟩,
  ⟨639, .sessionEvent, 1427039018435236, 1, 297, 300⟩,
  ⟨640, .sessionEvent, 1427039018887638, 1, 297, 300⟩,
  ⟨641, .sessionEvent, 1427039023719446, 1, 297, 305⟩,
  ⟨642, .sessionEvent, 1427039116282011, 1, 297, 262⟩,
  ⟨643, .sessionEvent, 1427039116282011, 1, 297, 262⟩,
  ⟨644, .sessionEvent, 1427039116344410, 1, 297, 262⟩,
  ⟨645, .sessionEvent, 1427039116344410, 1, 297, 262⟩,
  ⟨646, .sessionEvent, 1427039117280413, 1, 297, 262⟩,
  ⟨647, .sessionEvent, 1427039131129238, 1, 297, 300⟩,
  ⟨648, .sessionEvent, 1427039145700264, 1, 297, 300⟩,
  ⟨649, .sessionEvent, 1427039257490059, 1, 297, 300⟩,
  ⟨650, .sessionEvent, 1427039624310112, 1, 297, 291⟩,
  ⟨651, .sessionEvent, 1427039624310112, 1, 297, 291⟩,
  ⟨652, .sessionEvent, 1427039624341311, 1, 297, 291⟩,
  ⟨653, .sessionEvent, 1427039624341311, 1, 297, 291⟩,
  ⟨654, .sessionEvent, 1427039625433313, 1, 297, 291⟩,
  ⟨655, .sessionEvent, 1427039752345053, 1, 301, 291⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 616) (.both (Sets.sessionRecorded 617) (.both (Sets.sessionRecorded 618) (.both (Sets.sessionRecorded 619) (.both (Sets.sessionRecorded 620) (.both (Sets.sessionRecorded 621) (.both (Sets.sessionRecorded 622) (.both (Sets.sessionRecorded 623) (.both (Sets.sessionRecorded 624) (.both (Sets.sessionRecorded 625) (.both (Sets.sessionRecorded 626) (.both (Sets.sessionRecorded 627) (.both (Sets.sessionRecorded 628) (.both (Sets.sessionRecorded 629) (.both (Sets.sessionRecorded 630) (.both (Sets.sessionRecorded 631) (.both (Sets.sessionRecorded 632) (.both (Sets.sessionRecorded 633) (.both (Sets.sessionRecorded 634) (.both (Sets.sessionRecorded 635) (.both (Sets.sessionRecorded 636) (.both (Sets.sessionRecorded 637) (.both (Sets.sessionRecorded 638) (.both (Sets.sessionRecorded 639) (.both (Sets.sessionRecorded 640) (.both (Sets.sessionRecorded 641) (.both (Sets.sessionRecorded 642) (.both (Sets.sessionRecorded 643) (.both (Sets.sessionRecorded 644) (.both (Sets.sessionRecorded 645) (.both (Sets.sessionRecorded 646) (.both (Sets.sessionRecorded 647) (.both (Sets.sessionRecorded 648) (.both (Sets.sessionRecorded 649) (.both (Sets.sessionRecorded 650) (.both (Sets.sessionRecorded 651) (.both (Sets.sessionRecorded 652) (.both (Sets.sessionRecorded 653) (.both (Sets.sessionRecorded 654) (Sets.sessionRecorded 655)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M234

#print axioms Cert.M234.verified
