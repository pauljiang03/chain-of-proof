import ChainOfProof
open ChainOfProof

namespace Cert.M245

def cited : List Fact := [
  ⟨997, .programRun, 1244666387328482, 1, 362, 363⟩,
  ⟨998, .programRun, 1244666388030473, 1, 364, 365⟩,
  ⟨999, .programRun, 1244666398856734, 1, 366, 367⟩,
  ⟨1000, .programRun, 1244668989251487, 1, 366, 368⟩,
  ⟨1001, .programRun, 1247534058243000, 1, 369, 370⟩,
  ⟨1002, .programRun, 1247534062829000, 1, 371, 372⟩,
  ⟨1003, .programRun, 1247534064545000, 1, 373, 374⟩,
  ⟨1004, .programRun, 1247534064545000, 1, 373, 375⟩,
  ⟨1005, .programRun, 1247534068632000, 1, 376, 377⟩,
  ⟨1006, .programRun, 1247534068632000, 1, 376, 378⟩,
  ⟨1007, .programRun, 1247534071705000, 1, 379, 380⟩,
  ⟨1008, .programRun, 1247534084872000, 1, 381, 382⟩,
  ⟨1009, .programRun, 1247534084996000, 1, 383, 384⟩,
  ⟨1010, .programRun, 1247534084996000, 1, 383, 385⟩,
  ⟨1011, .programRun, 1247534085605000, 1, 386, 387⟩,
  ⟨1012, .programRun, 1247534114496000, 1, 388, 389⟩,
  ⟨1013, .programRun, 1247534141530000, 1, 390, 391⟩,
  ⟨1014, .programRun, 1247535532387000, 1, 392, 393⟩,
  ⟨1015, .programRun, 1247535537769000, 1, 394, 395⟩,
  ⟨1016, .programRun, 1247535541841000, 1, 396, 397⟩,
  ⟨1017, .programRun, 1247535542948000, 1, 398, 399⟩,
  ⟨1018, .programRun, 1247535542979000, 1, 400, 401⟩,
  ⟨1019, .programRun, 1247535546177000, 1, 402, 403⟩,
  ⟨1020, .programRun, 1247535546552000, 1, 404, 405⟩,
  ⟨1021, .programRun, 1247535546552000, 1, 406, 407⟩,
  ⟨1022, .programRun, 1247535546552000, 1, 406, 408⟩,
  ⟨1023, .programRun, 1247535546583000, 1, 409, 410⟩,
  ⟨1024, .programRun, 1247535546583000, 1, 409, 411⟩,
  ⟨1025, .programRun, 1247535546583000, 1, 409, 412⟩,
  ⟨1026, .programRun, 1247535546583000, 1, 409, 413⟩,
  ⟨1027, .programRun, 1247535546583000, 1, 409, 414⟩,
  ⟨1028, .programRun, 1247535546583000, 1, 409, 415⟩,
  ⟨1029, .programRun, 1247535546583000, 1, 409, 416⟩,
  ⟨1030, .programRun, 1247535546583000, 1, 409, 417⟩,
  ⟨1031, .programRun, 1247535546583000, 1, 409, 418⟩,
  ⟨1032, .programRun, 1247535546583000, 1, 409, 419⟩,
  ⟨1033, .programRun, 1247535546583000, 1, 409, 420⟩,
  ⟨1034, .programRun, 1247535546583000, 1, 409, 421⟩,
  ⟨1035, .programRun, 1247535546926000, 1, 369, 422⟩,
  ⟨1036, .programRun, 1247535547472000, 1, 423, 424⟩ ]

def claim : Claim := .both (Sets.programRan 997) (.both (Sets.programRan 998) (.both (Sets.programRan 999) (.both (Sets.programRan 1000) (.both (Sets.programRan 1001) (.both (Sets.programRan 1002) (.both (Sets.programRan 1003) (.both (Sets.programRan 1004) (.both (Sets.programRan 1005) (.both (Sets.programRan 1006) (.both (Sets.programRan 1007) (.both (Sets.programRan 1008) (.both (Sets.programRan 1009) (.both (Sets.programRan 1010) (.both (Sets.programRan 1011) (.both (Sets.programRan 1012) (.both (Sets.programRan 1013) (.both (Sets.programRan 1014) (.both (Sets.programRan 1015) (.both (Sets.programRan 1016) (.both (Sets.programRan 1017) (.both (Sets.programRan 1018) (.both (Sets.programRan 1019) (.both (Sets.programRan 1020) (.both (Sets.programRan 1021) (.both (Sets.programRan 1022) (.both (Sets.programRan 1023) (.both (Sets.programRan 1024) (.both (Sets.programRan 1025) (.both (Sets.programRan 1026) (.both (Sets.programRan 1027) (.both (Sets.programRan 1028) (.both (Sets.programRan 1029) (.both (Sets.programRan 1030) (.both (Sets.programRan 1031) (.both (Sets.programRan 1032) (.both (Sets.programRan 1033) (.both (Sets.programRan 1034) (.both (Sets.programRan 1035) (Sets.programRan 1036)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M245

#print axioms Cert.M245.verified
