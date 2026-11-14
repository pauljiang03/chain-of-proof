import ChainOfProof
open ChainOfProof

namespace Cert.M232

def cited : List Fact := [
  ⟨536, .sessionEvent, 1290311240945242, 1, 297, 295⟩,
  ⟨537, .sessionEvent, 1290311912153975, 1, 298, 0⟩,
  ⟨538, .sessionEvent, 1290311915008780, 1, 298, 0⟩,
  ⟨539, .sessionEvent, 1427034833237000, 1, 299, 0⟩,
  ⟨540, .sessionEvent, 1427034833237000, 1, 299, 0⟩,
  ⟨541, .sessionEvent, 1427034864717855, 1, 297, 300⟩,
  ⟨542, .sessionEvent, 1427034868922289, 1, 297, 262⟩,
  ⟨543, .sessionEvent, 1427034868922289, 1, 297, 262⟩,
  ⟨544, .sessionEvent, 1427034871418293, 1, 297, 262⟩,
  ⟨545, .sessionEvent, 1427034871418293, 1, 297, 262⟩,
  ⟨546, .sessionEvent, 1427034881901512, 1, 297, 262⟩,
  ⟨547, .sessionEvent, 1427034889529924, 1, 297, 300⟩,
  ⟨548, .sessionEvent, 1427035093000000, 1000000, 298, 0⟩,
  ⟨549, .sessionEvent, 1427035095000000, 1000000, 298, 0⟩,
  ⟨550, .sessionEvent, 1427035095888088, 1, 301, 262⟩,
  ⟨551, .sessionEvent, 1427035095919289, 1, 301, 262⟩,
  ⟨552, .sessionEvent, 1427035095919289, 1, 301, 262⟩,
  ⟨553, .sessionEvent, 1427035095966089, 1, 301, 262⟩,
  ⟨554, .sessionEvent, 1427035096000000, 1000000, 298, 0⟩,
  ⟨555, .sessionEvent, 1427035096402891, 1, 298, 0⟩,
  ⟨556, .sessionEvent, 1427035098633694, 1, 298, 0⟩,
  ⟨557, .sessionEvent, 1427035099335695, 1, 298, 0⟩,
  ⟨558, .sessionEvent, 1427035859593599, 1, 302, 0⟩,
  ⟨559, .sessionEvent, 1427035859609200, 1, 302, 0⟩,
  ⟨560, .sessionEvent, 1427035874039225, 1, 302, 0⟩,
  ⟨561, .sessionEvent, 1427035874086025, 1, 297, 300⟩,
  ⟨562, .sessionEvent, 1427035875193626, 1, 297, 300⟩,
  ⟨563, .sessionEvent, 1427035875692829, 1, 297, 303⟩,
  ⟨564, .sessionEvent, 1427035876000000, 1000000, 302, 0⟩,
  ⟨565, .sessionEvent, 1427035876000000, 1000000, 302, 0⟩,
  ⟨566, .sessionEvent, 1427035876207628, 1, 297, 304⟩,
  ⟨567, .sessionEvent, 1427035876660030, 1, 297, 300⟩,
  ⟨568, .sessionEvent, 1427035876675631, 1, 297, 300⟩,
  ⟨569, .sessionEvent, 1427035880216837, 1, 297, 300⟩,
  ⟨570, .sessionEvent, 1427035887299248, 1, 297, 305⟩,
  ⟨571, .sessionEvent, 1427036010717463, 1, 297, 300⟩,
  ⟨572, .sessionEvent, 1427036011981066, 1, 297, 300⟩,
  ⟨573, .sessionEvent, 1427036019874680, 1, 297, 262⟩,
  ⟨574, .sessionEvent, 1427036019874680, 1, 297, 262⟩,
  ⟨575, .sessionEvent, 1427036019905880, 1, 297, 262⟩ ]

def claim : Claim := .both (Sets.sessionRecorded 536) (.both (Sets.sessionRecorded 537) (.both (Sets.sessionRecorded 538) (.both (Sets.sessionRecorded 539) (.both (Sets.sessionRecorded 540) (.both (Sets.sessionRecorded 541) (.both (Sets.sessionRecorded 542) (.both (Sets.sessionRecorded 543) (.both (Sets.sessionRecorded 544) (.both (Sets.sessionRecorded 545) (.both (Sets.sessionRecorded 546) (.both (Sets.sessionRecorded 547) (.both (Sets.sessionRecorded 548) (.both (Sets.sessionRecorded 549) (.both (Sets.sessionRecorded 550) (.both (Sets.sessionRecorded 551) (.both (Sets.sessionRecorded 552) (.both (Sets.sessionRecorded 553) (.both (Sets.sessionRecorded 554) (.both (Sets.sessionRecorded 555) (.both (Sets.sessionRecorded 556) (.both (Sets.sessionRecorded 557) (.both (Sets.sessionRecorded 558) (.both (Sets.sessionRecorded 559) (.both (Sets.sessionRecorded 560) (.both (Sets.sessionRecorded 561) (.both (Sets.sessionRecorded 562) (.both (Sets.sessionRecorded 563) (.both (Sets.sessionRecorded 564) (.both (Sets.sessionRecorded 565) (.both (Sets.sessionRecorded 566) (.both (Sets.sessionRecorded 567) (.both (Sets.sessionRecorded 568) (.both (Sets.sessionRecorded 569) (.both (Sets.sessionRecorded 570) (.both (Sets.sessionRecorded 571) (.both (Sets.sessionRecorded 572) (.both (Sets.sessionRecorded 573) (.both (Sets.sessionRecorded 574) (Sets.sessionRecorded 575)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M232

#print axioms Cert.M232.verified
