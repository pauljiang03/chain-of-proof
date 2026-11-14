import ChainOfProof
open ChainOfProof

namespace Cert.M239

def cited : List Fact := [
  ⟨816, .sessionEvent, 1427279596811525, 1, 297, 300⟩,
  ⟨817, .sessionEvent, 1427279599369930, 1, 297, 305⟩,
  ⟨818, .sessionEvent, 1427279665685648, 1, 299, 0⟩,
  ⟨819, .sessionEvent, 1427288722609200, 1, 302, 0⟩,
  ⟨820, .sessionEvent, 1427288722624800, 1, 302, 0⟩,
  ⟨821, .sessionEvent, 1427288741968834, 1, 297, 300⟩,
  ⟨822, .sessionEvent, 1427288741968834, 1, 302, 0⟩,
  ⟨823, .sessionEvent, 1427288742592834, 1, 297, 300⟩,
  ⟨824, .sessionEvent, 1427288743000000, 1000000, 302, 0⟩,
  ⟨825, .sessionEvent, 1427288743000000, 1000000, 302, 0⟩,
  ⟨826, .sessionEvent, 1427288743372837, 1, 297, 303⟩,
  ⟨827, .sessionEvent, 1427288743497637, 1, 297, 304⟩,
  ⟨828, .sessionEvent, 1427288743638037, 1, 297, 300⟩,
  ⟨829, .sessionEvent, 1427288743669237, 1, 297, 300⟩,
  ⟨830, .sessionEvent, 1427288745556839, 1, 297, 300⟩,
  ⟨831, .sessionEvent, 1427288748117256, 1, 297, 305⟩,
  ⟨832, .sessionEvent, 1427288768919298, 1, 297, 262⟩,
  ⟨833, .sessionEvent, 1427288768919298, 1, 297, 262⟩,
  ⟨834, .sessionEvent, 1427288768919299, 1, 297, 262⟩,
  ⟨835, .sessionEvent, 1427288768966099, 1, 297, 262⟩,
  ⟨836, .sessionEvent, 1427288768981699, 1, 297, 262⟩,
  ⟨837, .sessionEvent, 1427288769153299, 1, 297, 262⟩,
  ⟨838, .sessionEvent, 1427288776402313, 1, 297, 300⟩,
  ⟨839, .sessionEvent, 1427288869222477, 1, 297, 300⟩,
  ⟨840, .sessionEvent, 1427289839668980, 1, 297, 300⟩,
  ⟨841, .sessionEvent, 1427292827009901, 1, 299, 0⟩,
  ⟨842, .sessionEvent, 1427292827009901, 1, 299, 0⟩,
  ⟨843, .sessionEvent, 1427292827025000, 1, 299, 0⟩,
  ⟨844, .sessionEvent, 1427292827025000, 1, 299, 0⟩,
  ⟨845, .sessionEvent, 1427293913299805, 1, 297, 300⟩,
  ⟨846, .sessionEvent, 1427294759180204, 1, 301, 262⟩,
  ⟨847, .sessionEvent, 1427294759180204, 1, 301, 262⟩,
  ⟨848, .sessionEvent, 1427294759180204, 1, 297, 262⟩,
  ⟨849, .sessionEvent, 1427294759180204, 1, 297, 262⟩,
  ⟨850, .sessionEvent, 1427294759180205, 1, 297, 262⟩,
  ⟨851, .sessionEvent, 1427295028948605, 1, 297, 300⟩,
  ⟨852, .sessionEvent, 1427295030305803, 1, 297, 300⟩,
  ⟨853, .sessionEvent, 1427295030430605, 1, 297, 300⟩,
  ⟨854, .sessionEvent, 1427295050960205, 1, 297, 300⟩,
  ⟨855, .sessionEvent, 1427295415922205, 1, 297, 300⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 816) (.both (Sets.sessionRecorded 817) (.both (Sets.sessionRecorded 818) (.both (Sets.sessionRecorded 819) (.both (Sets.sessionRecorded 820) (.both (Sets.sessionRecorded 821) (.both (Sets.sessionRecorded 822) (.both (Sets.sessionRecorded 823) (.both (Sets.sessionRecorded 824) (.both (Sets.sessionRecorded 825) (.both (Sets.sessionRecorded 826) (.both (Sets.sessionRecorded 827) (.both (Sets.sessionRecorded 828) (.both (Sets.sessionRecorded 829) (.both (Sets.sessionRecorded 830) (.both (Sets.sessionRecorded 831) (.both (Sets.sessionRecorded 832) (.both (Sets.sessionRecorded 833) (.both (Sets.sessionRecorded 834) (.both (Sets.sessionRecorded 835) (.both (Sets.sessionRecorded 836) (.both (Sets.sessionRecorded 837) (.both (Sets.sessionRecorded 838) (.both (Sets.sessionRecorded 839) (.both (Sets.sessionRecorded 840) (.both (Sets.sessionRecorded 841) (.both (Sets.sessionRecorded 842) (.both (Sets.sessionRecorded 843) (.both (Sets.sessionRecorded 844) (.both (Sets.sessionRecorded 845) (.both (Sets.sessionRecorded 846) (.both (Sets.sessionRecorded 847) (.both (Sets.sessionRecorded 848) (.both (Sets.sessionRecorded 849) (.both (Sets.sessionRecorded 850) (.both (Sets.sessionRecorded 851) (.both (Sets.sessionRecorded 852) (.both (Sets.sessionRecorded 853) (.both (Sets.sessionRecorded 854) (Sets.sessionRecorded 855)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M239

#print axioms Cert.M239.verified
