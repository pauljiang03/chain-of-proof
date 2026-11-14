import ChainOfProof
open ChainOfProof

namespace Cert.M241

def cited : List Fact := [
  ⟨870, .programInstalled, 1247547205796017, 1, 306, 0⟩,
  ⟨871, .programInstalled, 1247547205796017, 1, 307, 0⟩,
  ⟨872, .programInstalled, 1247547205796017, 1, 308, 0⟩,
  ⟨873, .programInstalled, 1247547205796017, 1, 309, 0⟩,
  ⟨874, .programInstalled, 1247547205796017, 1, 310, 0⟩,
  ⟨875, .programInstalled, 1247547205796017, 1, 311, 0⟩,
  ⟨876, .programInstalled, 1247547205796017, 1, 312, 0⟩,
  ⟨877, .programInstalled, 1247547205796017, 1, 313, 0⟩,
  ⟨878, .programInstalled, 1247547205796017, 1, 314, 0⟩,
  ⟨879, .programInstalled, 1247547205796017, 1, 315, 0⟩,
  ⟨880, .programInstalled, 1247547205796017, 1, 316, 0⟩,
  ⟨881, .programInstalled, 1247547206154819, 1, 306, 0⟩,
  ⟨882, .programInstalled, 1247547206154819, 1, 307, 0⟩,
  ⟨883, .programInstalled, 1247547206154819, 1, 308, 0⟩,
  ⟨884, .programInstalled, 1247547206154819, 1, 309, 0⟩,
  ⟨885, .programInstalled, 1247547206154819, 1, 310, 0⟩,
  ⟨886, .programInstalled, 1247547206154819, 1, 311, 0⟩,
  ⟨887, .programInstalled, 1247547206154819, 1, 312, 0⟩,
  ⟨888, .programInstalled, 1247547206154819, 1, 313, 0⟩,
  ⟨889, .programInstalled, 1247547206154819, 1, 314, 0⟩,
  ⟨890, .programInstalled, 1247547206154819, 1, 315, 0⟩,
  ⟨891, .programInstalled, 1247547206154819, 1, 316, 0⟩,
  ⟨892, .programInstalled, 1426996800000000, 86400000000, 317, 318⟩,
  ⟨893, .programInstalled, 1426996800000000, 86400000000, 319, 320⟩,
  ⟨894, .programInstalled, 1426996800000000, 86400000000, 321, 322⟩,
  ⟨895, .programInstalled, 1426996800000000, 86400000000, 323, 322⟩,
  ⟨896, .programInstalled, 1426996800000000, 86400000000, 324, 322⟩,
  ⟨897, .programInstalled, 1426996800000000, 86400000000, 325, 322⟩,
  ⟨898, .programInstalled, 1426996800000000, 86400000000, 326, 322⟩,
  ⟨899, .programInstalled, 1426996800000000, 86400000000, 327, 322⟩,
  ⟨900, .programInstalled, 1426996800000000, 86400000000, 328, 322⟩,
  ⟨901, .programInstalled, 1426996800000000, 86400000000, 329, 322⟩,
  ⟨902, .programInstalled, 1426996800000000, 86400000000, 330, 322⟩,
  ⟨903, .programInstalled, 1426996800000000, 86400000000, 331, 322⟩,
  ⟨904, .programInstalled, 1426996800000000, 86400000000, 332, 322⟩,
  ⟨905, .programInstalled, 1426996800000000, 86400000000, 333, 322⟩,
  ⟨906, .programInstalled, 1426996800000000, 86400000000, 334, 322⟩,
  ⟨907, .programInstalled, 1426996800000000, 86400000000, 335, 322⟩,
  ⟨908, .programInstalled, 1426996800000000, 86400000000, 336, 322⟩,
  ⟨909, .programInstalled, 1426996800000000, 86400000000, 337, 322⟩ ]

def claim : Claim := .both (Sets.programInstalledAt 870) (.both (Sets.programInstalledAt 871) (.both (Sets.programInstalledAt 872) (.both (Sets.programInstalledAt 873) (.both (Sets.programInstalledAt 874) (.both (Sets.programInstalledAt 875) (.both (Sets.programInstalledAt 876) (.both (Sets.programInstalledAt 877) (.both (Sets.programInstalledAt 878) (.both (Sets.programInstalledAt 879) (.both (Sets.programInstalledAt 880) (.both (Sets.programInstalledAt 881) (.both (Sets.programInstalledAt 882) (.both (Sets.programInstalledAt 883) (.both (Sets.programInstalledAt 884) (.both (Sets.programInstalledAt 885) (.both (Sets.programInstalledAt 886) (.both (Sets.programInstalledAt 887) (.both (Sets.programInstalledAt 888) (.both (Sets.programInstalledAt 889) (.both (Sets.programInstalledAt 890) (.both (Sets.programInstalledAt 891) (.both (Sets.programInstalledAt 892) (.both (Sets.programInstalledAt 893) (.both (Sets.programInstalledAt 894) (.both (Sets.programInstalledAt 895) (.both (Sets.programInstalledAt 896) (.both (Sets.programInstalledAt 897) (.both (Sets.programInstalledAt 898) (.both (Sets.programInstalledAt 899) (.both (Sets.programInstalledAt 900) (.both (Sets.programInstalledAt 901) (.both (Sets.programInstalledAt 902) (.both (Sets.programInstalledAt 903) (.both (Sets.programInstalledAt 904) (.both (Sets.programInstalledAt 905) (.both (Sets.programInstalledAt 906) (.both (Sets.programInstalledAt 907) (.both (Sets.programInstalledAt 908) (Sets.programInstalledAt 909)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M241

#print axioms Cert.M241.verified
