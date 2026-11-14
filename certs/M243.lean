import ChainOfProof
open ChainOfProof

namespace Cert.M243

def cited : List Fact := [
  ⟨950, .programInstalled, 1427036492418913, 1, 333, 322⟩,
  ⟨951, .programInstalled, 1427036494000000, 1000000, 330, 322⟩,
  ⟨952, .programInstalled, 1427036494000000, 1000000, 331, 322⟩,
  ⟨953, .programInstalled, 1427036494010117, 1, 330, 322⟩,
  ⟨954, .programInstalled, 1427036494696516, 1, 331, 322⟩,
  ⟨955, .programInstalled, 1427036497000000, 1000000, 340, 322⟩,
  ⟨956, .programInstalled, 1427036497161322, 1, 340, 322⟩,
  ⟨957, .programInstalled, 1427036498939724, 1, 343, 322⟩,
  ⟨958, .programInstalled, 1427036499000000, 1000000, 343, 322⟩,
  ⟨959, .programInstalled, 1427036506000000, 1000000, 329, 322⟩,
  ⟨960, .programInstalled, 1427036506568136, 1, 329, 322⟩,
  ⟨961, .programInstalled, 1427036613397125, 1, 332, 322⟩,
  ⟨962, .programInstalled, 1427036654939999, 1, 332, 322⟩,
  ⟨963, .programInstalled, 1427036658000000, 1000000, 332, 322⟩,
  ⟨964, .programInstalled, 1427037111924021, 1, 317, 318⟩,
  ⟨965, .programInstalled, 1427037363000000, 1000000, 319, 320⟩,
  ⟨966, .programInstalled, 1427037363240541, 1, 319, 320⟩,
  ⟨967, .programInstalled, 1427083200000000, 86400000000, 345, 346⟩,
  ⟨968, .programInstalled, 1427083200000000, 86400000000, 347, 348⟩,
  ⟨969, .programInstalled, 1427083200000000, 86400000000, 349, 350⟩,
  ⟨970, .programInstalled, 1427083200000000, 86400000000, 351, 352⟩,
  ⟨971, .programInstalled, 1427083200000000, 86400000000, 353, 354⟩,
  ⟨972, .programInstalled, 1427140821000000, 1000000, 353, 354⟩,
  ⟨973, .programInstalled, 1427140822000000, 1000000, 353, 354⟩,
  ⟨974, .programInstalled, 1427140845558678, 1, 345, 346⟩,
  ⟨975, .programInstalled, 1427140852000000, 1000000, 345, 346⟩,
  ⟨976, .programInstalled, 1427140858000000, 1000000, 349, 350⟩,
  ⟨977, .programInstalled, 1427140858046947, 1, 349, 350⟩,
  ⟨978, .programInstalled, 1427140861000000, 1000000, 347, 348⟩,
  ⟨979, .programInstalled, 1427140861463352, 1, 347, 348⟩,
  ⟨980, .programInstalled, 1427140914337250, 1, 353, 354⟩,
  ⟨981, .programInstalled, 1427140922000000, 1000000, 353, 354⟩,
  ⟨982, .programInstalled, 1427140966000000, 1000000, 351, 352⟩,
  ⟨983, .programInstalled, 1427140966088800, 1, 351, 352⟩,
  ⟨984, .programInstalled, 1427256000000000, 86400000000, 355, 356⟩,
  ⟨985, .programInstalled, 1427256000000000, 86400000000, 357, 358⟩,
  ⟨986, .programInstalled, 1427256000000000, 86400000000, 359, 358⟩,
  ⟨987, .programInstalled, 1427278521708046, 1, 360, 0⟩,
  ⟨988, .programInstalled, 1427278521708046, 1, 361, 0⟩,
  ⟨989, .programInstalled, 1427295099148603, 1, 357, 358⟩ ]

def claim : Claim := .both (Sets.programInstalledAt 950) (.both (Sets.programInstalledAt 951) (.both (Sets.programInstalledAt 952) (.both (Sets.programInstalledAt 953) (.both (Sets.programInstalledAt 954) (.both (Sets.programInstalledAt 955) (.both (Sets.programInstalledAt 956) (.both (Sets.programInstalledAt 957) (.both (Sets.programInstalledAt 958) (.both (Sets.programInstalledAt 959) (.both (Sets.programInstalledAt 960) (.both (Sets.programInstalledAt 961) (.both (Sets.programInstalledAt 962) (.both (Sets.programInstalledAt 963) (.both (Sets.programInstalledAt 964) (.both (Sets.programInstalledAt 965) (.both (Sets.programInstalledAt 966) (.both (Sets.programInstalledAt 967) (.both (Sets.programInstalledAt 968) (.both (Sets.programInstalledAt 969) (.both (Sets.programInstalledAt 970) (.both (Sets.programInstalledAt 971) (.both (Sets.programInstalledAt 972) (.both (Sets.programInstalledAt 973) (.both (Sets.programInstalledAt 974) (.both (Sets.programInstalledAt 975) (.both (Sets.programInstalledAt 976) (.both (Sets.programInstalledAt 977) (.both (Sets.programInstalledAt 978) (.both (Sets.programInstalledAt 979) (.both (Sets.programInstalledAt 980) (.both (Sets.programInstalledAt 981) (.both (Sets.programInstalledAt 982) (.both (Sets.programInstalledAt 983) (.both (Sets.programInstalledAt 984) (.both (Sets.programInstalledAt 985) (.both (Sets.programInstalledAt 986) (.both (Sets.programInstalledAt 987) (.both (Sets.programInstalledAt 988) (Sets.programInstalledAt 989)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M243

#print axioms Cert.M243.verified
