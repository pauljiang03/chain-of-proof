import ChainOfProof
open ChainOfProof

namespace Cert.M309

def cited : List Fact := [
  ⟨11730, .fileSeen, 1427039324819778, 1, 15889, 15339⟩,
  ⟨11731, .fileSeen, 1427039597298463, 1, 15505, 15339⟩,
  ⟨11732, .fileSeen, 1427039597314063, 1, 15505, 15339⟩,
  ⟨11733, .fileSeen, 1427039624341311, 1, 15890, 15339⟩,
  ⟨11734, .fileSeen, 1427039624388111, 1, 15891, 15453⟩,
  ⟨11735, .fileSeen, 1427039624388111, 1, 15891, 15339⟩,
  ⟨11736, .fileSeen, 1427039624450511, 1, 15892, 15339⟩,
  ⟨11737, .fileSeen, 1427039624450511, 1, 15893, 15339⟩,
  ⟨11738, .fileSeen, 1427039624450511, 1, 15894, 15339⟩,
  ⟨11739, .fileSeen, 1427039624450511, 1, 15895, 15339⟩,
  ⟨11740, .fileSeen, 1427039624450511, 1, 15896, 15339⟩,
  ⟨11741, .fileSeen, 1427039624450511, 1, 15897, 15339⟩,
  ⟨11742, .fileSeen, 1427039624450511, 1, 15898, 15339⟩,
  ⟨11743, .fileSeen, 1427039624450511, 1, 15899, 15339⟩,
  ⟨11744, .fileSeen, 1427039624450511, 1, 15900, 15339⟩,
  ⟨11745, .fileSeen, 1427039624466111, 1, 15901, 15339⟩,
  ⟨11746, .fileSeen, 1427039624606511, 1, 15902, 15339⟩,
  ⟨11747, .fileSeen, 1427039624606511, 1, 15903, 15453⟩,
  ⟨11748, .fileSeen, 1427039624606511, 1, 15903, 15339⟩,
  ⟨11749, .fileSeen, 1427039624606511, 1, 15904, 15339⟩,
  ⟨11750, .fileSeen, 1427039624637711, 1, 15905, 15339⟩,
  ⟨11751, .fileSeen, 1427039624684511, 1, 15906, 15339⟩,
  ⟨11752, .fileSeen, 1427039624715711, 1, 15890, 15339⟩,
  ⟨11753, .fileSeen, 1427039624778112, 1, 15901, 15339⟩,
  ⟨11754, .fileSeen, 1427039624778112, 1, 15907, 15339⟩,
  ⟨11755, .fileSeen, 1427039627071316, 1, 15901, 15339⟩,
  ⟨11756, .fileSeen, 1427039627196116, 1, 15860, 15339⟩,
  ⟨11757, .fileSeen, 1427039627211716, 1, 15442, 15339⟩,
  ⟨11758, .fileSeen, 1427039627211716, 1, 15848, 15339⟩,
  ⟨11759, .fileSeen, 1427039628132117, 1, 15469, 15339⟩,
  ⟨11760, .fileSeen, 1427039628194518, 1, 15358, 15339⟩,
  ⟨11761, .fileSeen, 1427039628194518, 1, 15359, 15339⟩,
  ⟨11762, .fileSeen, 1427039628194518, 1, 15470, 15339⟩,
  ⟨11763, .fileSeen, 1427039628210118, 1, 15360, 15339⟩,
  ⟨11764, .fileSeen, 1427039628210118, 1, 15361, 15339⟩,
  ⟨11765, .fileSeen, 1427039628225718, 1, 15357, 15339⟩,
  ⟨11766, .fileSeen, 1427039628225718, 1, 15462, 15339⟩,
  ⟨11767, .fileSeen, 1427039628225718, 1, 15463, 15339⟩,
  ⟨11768, .fileSeen, 1427039628256918, 1, 15908, 15339⟩,
  ⟨11769, .fileSeen, 1427039628256918, 1, 15909, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 11730) (.both (Sets.fileRecorded 11731) (.both (Sets.fileRecorded 11732) (.both (Sets.fileRecorded 11733) (.both (Sets.fileRecorded 11734) (.both (Sets.fileRecorded 11735) (.both (Sets.fileRecorded 11736) (.both (Sets.fileRecorded 11737) (.both (Sets.fileRecorded 11738) (.both (Sets.fileRecorded 11739) (.both (Sets.fileRecorded 11740) (.both (Sets.fileRecorded 11741) (.both (Sets.fileRecorded 11742) (.both (Sets.fileRecorded 11743) (.both (Sets.fileRecorded 11744) (.both (Sets.fileRecorded 11745) (.both (Sets.fileRecorded 11746) (.both (Sets.fileRecorded 11747) (.both (Sets.fileRecorded 11748) (.both (Sets.fileRecorded 11749) (.both (Sets.fileRecorded 11750) (.both (Sets.fileRecorded 11751) (.both (Sets.fileRecorded 11752) (.both (Sets.fileRecorded 11753) (.both (Sets.fileRecorded 11754) (.both (Sets.fileRecorded 11755) (.both (Sets.fileRecorded 11756) (.both (Sets.fileRecorded 11757) (.both (Sets.fileRecorded 11758) (.both (Sets.fileRecorded 11759) (.both (Sets.fileRecorded 11760) (.both (Sets.fileRecorded 11761) (.both (Sets.fileRecorded 11762) (.both (Sets.fileRecorded 11763) (.both (Sets.fileRecorded 11764) (.both (Sets.fileRecorded 11765) (.both (Sets.fileRecorded 11766) (.both (Sets.fileRecorded 11767) (.both (Sets.fileRecorded 11768) (Sets.fileRecorded 11769)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M309

#print axioms Cert.M309.verified
