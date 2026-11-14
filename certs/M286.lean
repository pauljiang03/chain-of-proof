import ChainOfProof
open ChainOfProof

namespace Cert.M286

def cited : List Fact := [
  ⟨10810, .fileSeen, 1247538848072764, 1, 15338, 15339⟩,
  ⟨10811, .fileSeen, 1247538848072764, 1, 15340, 15339⟩,
  ⟨10812, .fileSeen, 1247538848072764, 1, 15341, 15339⟩,
  ⟨10813, .fileSeen, 1247538899801370, 1, 15342, 15339⟩,
  ⟨10814, .fileSeen, 1247538899816969, 1, 15343, 15339⟩,
  ⟨10815, .fileSeen, 1247538899832569, 1, 15344, 15339⟩,
  ⟨10816, .fileSeen, 1247538899832569, 1, 15345, 15339⟩,
  ⟨10817, .fileSeen, 1247538899832569, 1, 15346, 15339⟩,
  ⟨10818, .fileSeen, 1247538899832569, 1, 15347, 15339⟩,
  ⟨10819, .fileSeen, 1247538899832569, 1, 15348, 15339⟩,
  ⟨10820, .fileSeen, 1247538899832569, 1, 15349, 15339⟩,
  ⟨10821, .fileSeen, 1247538899879368, 1, 15350, 15339⟩,
  ⟨10822, .fileSeen, 1247539002353797, 1, 15351, 15339⟩,
  ⟨10823, .fileSeen, 1247539002369397, 1, 15352, 15339⟩,
  ⟨10824, .fileSeen, 1247539002400597, 1, 15353, 15339⟩,
  ⟨10825, .fileSeen, 1247539002431796, 1, 15354, 15339⟩,
  ⟨10826, .fileSeen, 1247541608836215, 1, 15355, 15339⟩,
  ⟨10827, .fileSeen, 1247541608836215, 1, 15356, 15339⟩,
  ⟨10828, .fileSeen, 1247541608836215, 1, 15357, 15339⟩,
  ⟨10829, .fileSeen, 1247541608836215, 1, 15358, 15339⟩,
  ⟨10830, .fileSeen, 1247541608836215, 1, 15359, 15339⟩,
  ⟨10831, .fileSeen, 1247541608836215, 1, 15360, 15339⟩,
  ⟨10832, .fileSeen, 1247541608836215, 1, 15361, 15339⟩,
  ⟨10833, .fileSeen, 1247541608851815, 1, 1456, 15339⟩,
  ⟨10834, .fileSeen, 1247541608851815, 1, 15362, 15339⟩,
  ⟨10835, .fileSeen, 1247541608883013, 1, 15343, 15339⟩,
  ⟨10836, .fileSeen, 1247541608914212, 1, 15363, 15339⟩,
  ⟨10837, .fileSeen, 1247541608914212, 1, 15344, 15339⟩,
  ⟨10838, .fileSeen, 1247541608914212, 1, 15345, 15339⟩,
  ⟨10839, .fileSeen, 1247541608914212, 1, 15346, 15339⟩,
  ⟨10840, .fileSeen, 1247541608914212, 1, 15347, 15339⟩,
  ⟨10841, .fileSeen, 1247541608929812, 1, 15348, 15339⟩,
  ⟨10842, .fileSeen, 1247541608929812, 1, 15350, 15339⟩,
  ⟨10843, .fileSeen, 1247541608929812, 1, 15349, 15339⟩,
  ⟨10844, .fileSeen, 1247541608929812, 1, 15364, 15339⟩,
  ⟨10845, .fileSeen, 1247541608945411, 1, 15342, 15339⟩,
  ⟨10846, .fileSeen, 1247541608945411, 1, 15365, 15339⟩,
  ⟨10847, .fileSeen, 1247541608945411, 1, 15366, 15339⟩,
  ⟨10848, .fileSeen, 1247541608945411, 1, 15367, 15339⟩,
  ⟨10849, .fileSeen, 1247541608961010, 1, 15368, 15339⟩ ]

def claim : Claim := .both (Sets.fileRecorded 10810) (.both (Sets.fileRecorded 10811) (.both (Sets.fileRecorded 10812) (.both (Sets.fileRecorded 10813) (.both (Sets.fileRecorded 10814) (.both (Sets.fileRecorded 10815) (.both (Sets.fileRecorded 10816) (.both (Sets.fileRecorded 10817) (.both (Sets.fileRecorded 10818) (.both (Sets.fileRecorded 10819) (.both (Sets.fileRecorded 10820) (.both (Sets.fileRecorded 10821) (.both (Sets.fileRecorded 10822) (.both (Sets.fileRecorded 10823) (.both (Sets.fileRecorded 10824) (.both (Sets.fileRecorded 10825) (.both (Sets.fileRecorded 10826) (.both (Sets.fileRecorded 10827) (.both (Sets.fileRecorded 10828) (.both (Sets.fileRecorded 10829) (.both (Sets.fileRecorded 10830) (.both (Sets.fileRecorded 10831) (.both (Sets.fileRecorded 10832) (.both (Sets.fileRecorded 10833) (.both (Sets.fileRecorded 10834) (.both (Sets.fileRecorded 10835) (.both (Sets.fileRecorded 10836) (.both (Sets.fileRecorded 10837) (.both (Sets.fileRecorded 10838) (.both (Sets.fileRecorded 10839) (.both (Sets.fileRecorded 10840) (.both (Sets.fileRecorded 10841) (.both (Sets.fileRecorded 10842) (.both (Sets.fileRecorded 10843) (.both (Sets.fileRecorded 10844) (.both (Sets.fileRecorded 10845) (.both (Sets.fileRecorded 10846) (.both (Sets.fileRecorded 10847) (.both (Sets.fileRecorded 10848) (Sets.fileRecorded 10849)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M286

#print axioms Cert.M286.verified
