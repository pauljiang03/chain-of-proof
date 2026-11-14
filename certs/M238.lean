import ChainOfProof
open ChainOfProof

namespace Cert.M238

def cited : List Fact := [
  ⟨776, .sessionEvent, 1427231245769718, 1, 301, 262⟩,
  ⟨777, .sessionEvent, 1427231246799320, 1, 298, 0⟩,
  ⟨778, .sessionEvent, 1427231247000000, 1000000, 298, 0⟩,
  ⟨779, .sessionEvent, 1427231248218922, 1, 298, 0⟩,
  ⟨780, .sessionEvent, 1427231249045724, 1, 298, 0⟩,
  ⟨781, .sessionEvent, 1427231249108124, 1, 298, 0⟩,
  ⟨782, .sessionEvent, 1427278495546799, 1, 302, 0⟩,
  ⟨783, .sessionEvent, 1427278535248869, 1, 302, 0⟩,
  ⟨784, .sessionEvent, 1427278535311270, 1, 297, 300⟩,
  ⟨785, .sessionEvent, 1427278537713673, 1, 297, 300⟩,
  ⟨786, .sessionEvent, 1427278538914877, 1, 297, 303⟩,
  ⟨787, .sessionEvent, 1427278546000000, 1000000, 302, 0⟩,
  ⟨788, .sessionEvent, 1427278546000000, 1000000, 302, 0⟩,
  ⟨789, .sessionEvent, 1427278546683689, 1, 297, 304⟩,
  ⟨790, .sessionEvent, 1427278546995691, 1, 297, 300⟩,
  ⟨791, .sessionEvent, 1427278547011292, 1, 297, 300⟩,
  ⟨792, .sessionEvent, 1427278547338890, 1, 297, 300⟩,
  ⟨793, .sessionEvent, 1427278550162495, 1, 297, 300⟩,
  ⟨794, .sessionEvent, 1427278554717703, 1, 297, 305⟩,
  ⟨795, .sessionEvent, 1427278675461916, 1, 297, 300⟩,
  ⟨796, .sessionEvent, 1427278677708319, 1, 297, 300⟩,
  ⟨797, .sessionEvent, 1427278703900766, 1, 297, 300⟩,
  ⟨798, .sessionEvent, 1427278704165966, 1, 297, 300⟩,
  ⟨799, .sessionEvent, 1427278706000000, 1000000, 298, 0⟩,
  ⟨800, .sessionEvent, 1427278709000000, 1000000, 298, 0⟩,
  ⟨801, .sessionEvent, 1427278709407576, 1, 298, 0⟩,
  ⟨802, .sessionEvent, 1427278710093977, 1, 298, 0⟩,
  ⟨803, .sessionEvent, 1427278710764778, 1, 298, 0⟩,
  ⟨804, .sessionEvent, 1427278710842777, 1, 298, 0⟩,
  ⟨805, .sessionEvent, 1427278727624800, 1, 302, 0⟩,
  ⟨806, .sessionEvent, 1427278766671669, 1, 302, 0⟩,
  ⟨807, .sessionEvent, 1427278766827669, 1, 297, 300⟩,
  ⟨808, .sessionEvent, 1427278769276873, 1, 297, 300⟩,
  ⟨809, .sessionEvent, 1427278770212875, 1, 297, 303⟩,
  ⟨810, .sessionEvent, 1427278786499304, 1, 297, 300⟩,
  ⟨811, .sessionEvent, 1427278786592903, 1, 297, 300⟩,
  ⟨812, .sessionEvent, 1427278786686502, 1, 297, 304⟩,
  ⟨813, .sessionEvent, 1427279593000000, 1000000, 302, 0⟩,
  ⟨814, .sessionEvent, 1427279593000000, 1000000, 302, 0⟩,
  ⟨815, .sessionEvent, 1427279594799122, 1, 297, 300⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 776) (.both (Sets.sessionRecorded 777) (.both (Sets.sessionRecorded 778) (.both (Sets.sessionRecorded 779) (.both (Sets.sessionRecorded 780) (.both (Sets.sessionRecorded 781) (.both (Sets.sessionRecorded 782) (.both (Sets.sessionRecorded 783) (.both (Sets.sessionRecorded 784) (.both (Sets.sessionRecorded 785) (.both (Sets.sessionRecorded 786) (.both (Sets.sessionRecorded 787) (.both (Sets.sessionRecorded 788) (.both (Sets.sessionRecorded 789) (.both (Sets.sessionRecorded 790) (.both (Sets.sessionRecorded 791) (.both (Sets.sessionRecorded 792) (.both (Sets.sessionRecorded 793) (.both (Sets.sessionRecorded 794) (.both (Sets.sessionRecorded 795) (.both (Sets.sessionRecorded 796) (.both (Sets.sessionRecorded 797) (.both (Sets.sessionRecorded 798) (.both (Sets.sessionRecorded 799) (.both (Sets.sessionRecorded 800) (.both (Sets.sessionRecorded 801) (.both (Sets.sessionRecorded 802) (.both (Sets.sessionRecorded 803) (.both (Sets.sessionRecorded 804) (.both (Sets.sessionRecorded 805) (.both (Sets.sessionRecorded 806) (.both (Sets.sessionRecorded 807) (.both (Sets.sessionRecorded 808) (.both (Sets.sessionRecorded 809) (.both (Sets.sessionRecorded 810) (.both (Sets.sessionRecorded 811) (.both (Sets.sessionRecorded 812) (.both (Sets.sessionRecorded 813) (.both (Sets.sessionRecorded 814) (Sets.sessionRecorded 815)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M238

#print axioms Cert.M238.verified
