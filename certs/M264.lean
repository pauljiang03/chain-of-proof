import ChainOfProof
open ChainOfProof

namespace Cert.M264

def cited : List Fact := [
  ⟨1755, .webVisit, 1427134067501178, 1, 1159, 1095⟩,
  ⟨1756, .webVisit, 1427134072314000, 1, 1160, 1095⟩,
  ⟨1757, .webVisit, 1427134072314187, 1, 1160, 1095⟩,
  ⟨1758, .webVisit, 1427134072314187, 1, 1160, 1095⟩,
  ⟨1759, .webVisit, 1427134074981000, 1, 1161, 1095⟩,
  ⟨1760, .webVisit, 1427134074981192, 1, 1161, 1095⟩,
  ⟨1761, .webVisit, 1427134074981192, 1, 1161, 1095⟩,
  ⟨1762, .webVisit, 1427134074991192, 1, 1161, 1095⟩,
  ⟨1763, .webVisit, 1427134076338695, 1, 1162, 1095⟩,
  ⟨1764, .webVisit, 1427134077288697, 1, 1160, 1095⟩,
  ⟨1765, .webVisit, 1427134077428697, 1, 1163, 1095⟩,
  ⟨1766, .webVisit, 1427134078080000, 1, 1164, 1095⟩,
  ⟨1767, .webVisit, 1427134078080701, 1, 1164, 1095⟩,
  ⟨1768, .webVisit, 1427134078080701, 1, 1164, 1095⟩,
  ⟨1769, .webVisit, 1427134079890000, 1, 1165, 1095⟩,
  ⟨1770, .webVisit, 1427134079890207, 1, 1165, 1095⟩,
  ⟨1771, .webVisit, 1427134079890207, 1, 1165, 1095⟩,
  ⟨1772, .webVisit, 1427134081920211, 1, 1166, 1095⟩,
  ⟨1773, .webVisit, 1427134094929245, 1, 1167, 1095⟩,
  ⟨1774, .webVisit, 1427134097473258, 1, 1168, 1095⟩,
  ⟨1775, .webVisit, 1427134098123259, 1, 1169, 1095⟩,
  ⟨1776, .webVisit, 1427134098133000, 1, 1169, 1095⟩,
  ⟨1777, .webVisit, 1427134098133259, 1, 1169, 1095⟩,
  ⟨1778, .webVisit, 1427134098473260, 1, 1169, 1095⟩,
  ⟨1779, .webVisit, 1427134103642268, 1, 1165, 1095⟩,
  ⟨1780, .webVisit, 1427134111817280, 1, 1170, 1095⟩,
  ⟨1781, .webVisit, 1427134114190285, 1, 1171, 1095⟩,
  ⟨1782, .webVisit, 1427134134101318, 1, 1172, 1095⟩,
  ⟨1783, .webVisit, 1427134135603822, 1, 1173, 1095⟩,
  ⟨1784, .webVisit, 1427134171496373, 1, 1174, 1095⟩,
  ⟨1785, .webVisit, 1427134173466378, 1, 1175, 1095⟩,
  ⟨1786, .webVisit, 1427134203820421, 1, 1176, 1095⟩,
  ⟨1787, .webVisit, 1427134205910426, 1, 1177, 1095⟩,
  ⟨1788, .webVisit, 1427134227643461, 1, 1178, 1095⟩,
  ⟨1789, .webVisit, 1427134229140965, 1, 1179, 1095⟩,
  ⟨1790, .webVisit, 1427134269687034, 1, 1180, 1095⟩,
  ⟨1791, .webVisit, 1427134269697034, 1, 1180, 1095⟩,
  ⟨1792, .webVisit, 1427134269697034, 1, 1181, 1095⟩,
  ⟨1793, .webVisit, 1427134270258040, 1, 1182, 1095⟩,
  ⟨1794, .webVisit, 1427134270259040, 1, 1182, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1755) (.both (Sets.visited 1756) (.both (Sets.visited 1757) (.both (Sets.visited 1758) (.both (Sets.visited 1759) (.both (Sets.visited 1760) (.both (Sets.visited 1761) (.both (Sets.visited 1762) (.both (Sets.visited 1763) (.both (Sets.visited 1764) (.both (Sets.visited 1765) (.both (Sets.visited 1766) (.both (Sets.visited 1767) (.both (Sets.visited 1768) (.both (Sets.visited 1769) (.both (Sets.visited 1770) (.both (Sets.visited 1771) (.both (Sets.visited 1772) (.both (Sets.visited 1773) (.both (Sets.visited 1774) (.both (Sets.visited 1775) (.both (Sets.visited 1776) (.both (Sets.visited 1777) (.both (Sets.visited 1778) (.both (Sets.visited 1779) (.both (Sets.visited 1780) (.both (Sets.visited 1781) (.both (Sets.visited 1782) (.both (Sets.visited 1783) (.both (Sets.visited 1784) (.both (Sets.visited 1785) (.both (Sets.visited 1786) (.both (Sets.visited 1787) (.both (Sets.visited 1788) (.both (Sets.visited 1789) (.both (Sets.visited 1790) (.both (Sets.visited 1791) (.both (Sets.visited 1792) (.both (Sets.visited 1793) (Sets.visited 1794)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M264

#print axioms Cert.M264.verified
