                                         Rtl2lean: Automated RTL-to-Lean Translation with
                                         Hierarchical Theorem Generation and Lemma Reuse
                                                Hongqin Lyu1,2 , Junxing Dong3 , Yonghao Wang1 Zhiteng Chao1 , Tiancheng Wang1,2 and Huawei Li1,2
                                                             1
                                                                 State Key Lab of Processors, Institute of Computing Technology, CAS, Beijing, China
                                                                            2
                                                                              University of Chinese Academy of Sciences, Beijing, China
                                                                                 3
                                                                                   NorthChina University of Science and Technology


                                            Abstract—Formal verification with interactive theorem provers      registers, pipeline depth, and overall state space increase, the
                                         can provide strong correctness guarantees for register transfer       solving process is often limited by state explosion and the
                                         level designs, but applying it to existing SystemVerilog code         rapid growth of constraints [4].
                                         requires substantial manual effort in semantic modeling and
                                         proof construction. This paper presents Rtl2lean, a framework            Unlike automated model checking, which relies on explor-
                                         that automatically translates RTL designs into executable Lean        ing a finite state space, interactive theorem provers such as
                                         4 models and builds a hierarchical theorem library for subse-         Lean 4 and Coq allow users to define hardware semantics
                                         quent verification. The generated model represents hardware           in formal logic and construct machine-checked proofs that
                                         execution as a pure state transition function, while a four layer     hold for arbitrary inputs and execution lengths. Lean 4 further
                                         theorem framework captures combinational semantics, sequential
                                                                                                               provides dependent types, extensible metaprogramming, and
arXiv:2607.16855v1 [cs.AR] 18 Jul 2026




                                         updates, single cycle behavior, and reachability and invariants.
                                         When a high level property cannot be discharged by the existing       efficient code generation, making it suitable both for express-
                                         theorem base, an LLM based proving loop proposes intermediate         ing RTL designs and their properties and for building domain-
                                         lemmas from the current proof context and Lean feedback. Only         specific proof automation [5]. Prior work such as Kami and
                                         lemmas accepted by the Lean kernel are added to the reusable          Silver Oak has shown that embedding hardware semantics
                                         lemma pool. Experiments on six SystemVerilog designs generate
                                         403 theorems, all of which are successfully checked by Lean.          in proof assistants can support modular and parameterized
                                         Among 358 foundational lemmas, 287 are available for automatic        verification while providing stronger correctness guarantees
                                         reuse, yielding a reusable lemma ratio of 80.2 percent. The results   than finite simulation and bounded checking [6], [7]. However,
                                         demonstrate that Rtl2lean can construct machine checked RTL           applying this approach to existing RTL designs remains costly.
                                         proof libraries with low checking overhead and substantial cross      The event-driven semantics of the verilog differ substantially
                                         property lemma reuse.
                                            Index Terms—RTL verification, Lean 4, theorem proving,
                                                                                                               from Lean’s reasoning model [8] based on pure functions and
                                         lemma generation, large language models                               type theory, while proofs of complex hardware properties often
                                                                                                               require manually constructed auxiliary definitions, invariants,
                                                                  I. I NTRODUCTION                             and intermediate lemmas.
                                                                                                                  Fortunately, large language models (LLMs) have recently
                                            As integrated circuits continue to grow in scale and com-          demonstrated strong heuristic reasoning capabilities in both
                                         plexity, register-transfer level (RTL) verification has become        code generation and formal theorem proving. Early work
                                         one of the most critical and costly stages in modern hardware         such as GPT-f showed that generative language models can
                                         development [1]. Processors and system-on-chip designs often          be used to predict formal proof steps [9]. LeanDojo further
                                         contain complex datapaths, control state machines, pipelined          introduced infrastructure for interacting with the Lean proof
                                         structures, and a large number of parameterized modules. Even         environment, extracting proof data, and retrieving relevant
                                         a minor error, such as a missing state transition, an unhandled       premises, and demonstrated that retrieval-based premise se-
                                         boundary condition, or an incorrect bit-vector operation, may         lection can improve automated theorem proving [10]. In the
                                         remain undetected until system integration or even after tape-        hardware domain, the recent CktFormalizer [11] framework
                                         out, leading to substantial debugging and repair costs. There-        translates natural-language hardware specifications into type-
                                         fore, establishing rigorous and scalable correctness guarantees       safe hardware descriptions embedded in Lean 4, and uses
                                         for RTL designs at an early stage is a central challenge in           Lean for compilation checking and functional equivalence
                                         hardware design automation.                                           proofs. Together, these studies suggest that LLMs can identify
                                            Existing RTL verification flows mainly rely on dynamic             promising reasoning steps from the current proof state and
                                         simulation, model checking, equivalence checking, and formal          existing proof libraries, thereby assisting theorem provers in
                                         verification based on SAT/SMT solvers. Simulation is practical        proof search.
                                         and scalable for engineering use, but it can examine only a              However, this paper focuses on a different yet complemen-
                                         finite set of input vectors and execution traces. Model checking      tary question: Can existing RTL designs be automatically
                                         and bounded model checking can automatically explore the              translated into a Lean 4 formal library, while large lan-
                                         state space and have been widely used for both hardware               guage models dynamically generate intermediate lemmas
                                         and software verification [2], [3]. However, as the number of         to improve the automation of RTL theorem proving?
Achieving this goal involves two main challenges. First, there      this principle, a proposition is represented as a type, while
is currently no tool that can automatically translate RTL           a proof of that proposition is represented as a term of the
into Lean 4 representations. Because RTL behavior is jointly        corresponding type. Proving a proposition P is therefore
determined by current inputs, register states, and combina-         equivalent to constructing a proof term p such that
tional and sequential logic, the resulting Lean model must
hide unnecessary Verilog execution details while faithfully                                     Γ ⊢ p : P.                       (2)
preserving the cycle-level semantics of the original design.        The Lean kernel checks whether the constructed term indeed
Second, proofs of complex RTL properties often rely on highly       has type P . A theorem is accepted only if its proof term passes
design-specific intermediate lemmas, such as state invariants,      kernel type checking.
bit-vector properties, and multi-cycle relations. These lemmas
are difficult to enumerate in advance and are also challenging      B. Definitions, Theorems, and Intermediate Lemmas
for existing proof automation techniques to generate directly.         A formal development is primarily composed of definitions,
   To address these challenges, we propose Rtl2lean, an LLM-        theorems, and lemmas. Definitions specify the objects being
assisted Lean 4 formal verification framework for RTL de-           reasoned about and their formal semantics. Theorems express
signs. First, we develop a lightweight RTL-to-Lean 4 compiler       the final correctness properties to be established, while lemmas
that translates combinational logic, state updates, and bit-        capture intermediate results that can be reused during the
vector operations into Lean definitions with explicit cycle-        proof.
level semantics, providing a unified representation for formally       Let T be the target theorem. When directly proving T is
specifying and proving RTL properties. Second, we integrate         difficult, the proof can be decomposed by first establishing a
an LLM into Lean’s interactive proof loop. When a proof             set of intermediate lemmas,
attempt fails, the framework collects the current proof goal,
relevant definitions, and error feedback, and uses the LLM                                  L1 , L2 , . . . , Ln ,               (3)
to generate candidate intermediate lemmas. Each generated           and then using them to derive the final result:
lemma must be verified by the Lean kernel before it can be
used to advance the proof.                                                       Γ ⊢ L1 ,   Γ ⊢ L2 ,       ...,      Γ ⊢ Ln ,    (4)
   The main contributions of this work are as follows:                                  Γ, L1 , L2 , . . . , Ln ⊢ T.             (5)
   1) An automated RTL-to-Lean translation flow is proposed
       to convert combinational logic, sequential state updates,    Intermediate lemmas do not alter the meaning of the target
       and fixed-width bit-vector operations into Lean defini-      theorem. Instead, they expose auxiliary properties required
       tions with explicit cycle-level semantics.                   by the proof and decompose a complex reasoning task into
   2) An LLM-assisted theorem proving mechanism is intro-           smaller logical obligations.
       duced to generate intermediate lemmas from the cur-                        III. F RAMEWORK OF RTL 2 LEAN
       rent proof goal, local context, and Lean error feedback
       through an iterative generate–check–repair process.             Before presenting the technical details, we first introduce
   3) Experiments on six SystemVerilog designs demonstrate          the overall workflow of rtl2lean, as illustrated in Fig. 1. The
       a 100 percent proof success rate and an 80.2 percent         framework consists of three stages.
       reusable lemma ratio.                                           1) RTL-to-Lean semantic compilation: translates Sys-
                                                                          temVerilog RTL into a pure functional state-transition
                      II. BACKGROUND                                      model in Lean 4
A. Interactive Theorem Proving                                         2) Theorem framework generation: constructs a four-layer
                                                                          proof skeleton covering combinational logic, sequential
   The goal of theorem proving is to establish that a propo-
                                                                          processes, single-cycle behavior, and reachability or
sition follows from a set of formally specified assumptions
                                                                          invariants.
through valid logical inference. Let Γ denote a logical context
                                                                       3) Autonomous proving with lemma reuse: proves high-
containing variables, assumptions, definitions, and previously
                                                                          level specifications through a Lean-guided feedback
proved results, and let P denote the proposition to be proved.
                                                                          loop and stores verified theorems in a lemma pool for
A proof task can be written as
                                                                          subsequent proof tasks.
                            Γ ⊢ P,                           (1)    A. RTL-to-Lean Semantic Compilation
where ⊢ indicates that P can be derived from the information           SystemVerilog combines width-sensitive operations, block-
contained in Γ using valid inference rules. A formal proof is       ing and non-blocking assignments, conditional control flow,
therefore a sequence of logically valid steps that transforms the   and distinct combinational and sequential processes, making a
initial goal into propositions that can be directly established     direct encoding into a theorem prover difficult to reason about.
from the context.                                                   To address this issue, rtl2lean first parses the RTL design
   Lean 4 is an interactive theorem prover based on dependent       with PySlang and constructs a typed abstract syntax tree.
type theory and the propositions-as-types principle. Under          The resulting syntax tree is then lowered into an intermediate
                                                   Fig. 1. RTL2LEAN framework.



representation, where conditional updates are normalized as        Fig. 2(a), the semantic lemma characterizes how the overflow
selection expressions and different assignment types retain        flag is computed, while the preservation lemma states that
their corresponding update semantics. After standard optimiza-     the counter register remains unchanged. The preservation
tions, such as constant folding, dead-code elimination, and        lemma is marked with Lean’s @[simp] attribute, allowing
common-subexpression elimination, the backend generates a          the simplifier to apply it automatically in subsequent proofs.
Lean 4 model consisting of State, Inputs, Outputs, and                2) Sequential-Block Lemmas: The second layer targets
a single-cycle transition function step.                           state-update functions generated from sequential processes
   The generated model represents hardware execution as a          such as always_ff. For each sequential function, the frame-
pure function. Given the current state s and input i, step(s, i)   work derives determinism lemmas, preservation lemmas for
returns the next state without side effects. For example, the      registers outside its write set, and reset-behavior lemmas when
behavior of a counter with reset and enable signals can be         a reset pattern is identified. Figure 2(b) shows a counter
abstracted as                                                      update, its functional determinism property, and preservation
                                                                  of an unwritten overflow register. These lemmas package
               init,
                                           i.rst = true,
                                                                   register-level behavior into reusable proof units and avoid
  step(s, i) = s[count ← s.count + 1], i.enable = true,            repeatedly unfolding the complete sequential function.
               
                 s,                         otherwise.
               
                                                                      3) Step-Level Theorems: The third layer is built around the
                                                             (6)   unified single-cycle transition function step, which combines
   This functional encoding preserves the cycle-level transition   reset handling, combinational evaluation, and sequential state
semantics of the RTL design while exposing an explicit state       updates. This layer captures module-level properties such as
relation on which subsequent theorems can be constructed.          reset behavior, transition determinism, output reflection, and
                                                                   finite-state machine transitions. In Fig. 2(c), reset assertion
B. Four-Layer Theorem Framework Generation                         forces the next state to equal the initial state, while an output-
   Although RTL-to-Lean compilation establishes an exe-            reflection lemma relates the externally observed count value
cutable formal semantics for the design, directly proving high-    to the corresponding internal register. Step-level theorems
level specifications may still require repeated unfolding of       therefore provide a direct interface for reasoning about the
combinational functions, sequential processes, and the single-     complete behavior of one hardware cycle.
cycle transition function. Such proofs quickly become verbose         4) Reachability and Invariants: The first three layers
and contain substantial redundant reasoning. To address this       characterize individual functions or a single transition step,
issue, rtl2lean automatically constructs a bottom-up four-layer    whereas many hardware specifications concern executions of
theorem framework from the generated Lean 4 model. Lower           arbitrary length. The fourth layer therefore introduces reacha-
layers capture local hardware semantics, while higher layers       bility to lift the single-cycle semantics of step to multi-cycle
reuse these results to establish cycle-level and multi-cycle       executions. As shown in Fig. 2(d), a state is reachable if it can
properties.                                                        be obtained from the initial state by folding step over a finite
   1) Combinational-Logic Lemmas: The first layer targets          input sequence. The framework then proves that reachability
functions generated from continuous assignments and com-           is preserved by one additional transition and introduces state
binational processes. For each combinational function, the         invariants over all reachable states. Such results provide an
framework generates semantic lemmas for updated fields and         induction basis for proving higher-level safety and functional
preservation lemmas for unaffected fields. As illustrated in       specifications.
                                                                     For a target theorem T , the proof context is represented as
                                                                                     C(T ) = (M, T, Lbase , Lpool ) ,             (7)
                                                                     where M denotes the generated Lean 4 model, Lbase is the
                                                                     set of automatically generated lower-layer lemmas, and Lpool
                                                                     contains reusable lemmas proved in earlier tasks.
                                                                        For example, a high-level property for the counter states that
                                                                     the register remains unchanged when neither reset nor enable
                                                                     is asserted:
                                                                     i.rst = false∧i.enable = false =⇒ step(s, i).count = s.count.
                                                                                                                                  (8)
                                                                     The system provides this target together with the definition of
                                                                     step, the sequential-update semantics, and relevant preserva-
                                                                     tion lemmas.
                                                                        2) Lean-Guided Proving and Lemma Reuse: Given the
                                                                     constructed proof task, the system first attempts to solve the
                                                                     target using the existing theorem base. If the proof remains
                                                                     incomplete, an LLM proposes candidate intermediate lemmas
                                                                     according to the current goal, relevant definitions, available
                                                                     lemmas, and Lean error messages. Each candidate is checked
                                                                     by the Lean kernel before use. Rejected candidates are returned
                                                                     to the LLM with diagnostic feedback, whereas accepted lem-
                                                                     mas are added to the lemma pool and used to continue the
                                                                     proof. The iterative process is expressed as
                                                                                                                  
                                                                                      pk+1 = Generate C(T ), ek ,                 (9)
                                                                     where pk is the k-th candidate proof and ek is the error
                                                                     returned by Lean. The loop terminates when
                                                                                          Check(T, pk ) = Pass.                  (10)
                                                                       After a successful proof, the lemma pool is updated as
                                                                                        Lk+1 = Lk ∪ {T } ∪ H,                    (11)
                                                                     where H denotes auxiliary lemmas or local have statements
                                                                     discovered during proof generation. Later proofs can reuse
      Fig. 2. Representative examples generated by the four-layer.   these results through tactics such as rw, apply, and simp,
                                                                     avoiding repeated unfolding of the underlying RTL semantics.
                                                                        For the counter property in Eq. (8), a valid proof can be
C. Autonomous Proving and Lemma Reuse                                written as
                                                                     theorem count_stable_when_disabled :
   The previous stages generate an executable Lean 4 model             forall (s : counterState) (i : counterInputs),
and a layered theorem base. However, high-level functional               i.rst = false ->
                                                                         i.enable = false ->
specifications often require design-specific intermediate results        (step s i).count = s.count := by
that cannot be derived by fixed proof templates alone. To ad-          intro s i hrst hen
dress this issue, Rtl2lean employs a Lean-guided autonomous            simp [step, proc_alwaysff, hrst, hen]
proving procedure. When the existing theorem base cannot             Once verified, this theorem can be reused to prove related
discharge the current goal, an LLM generates candidate in-           properties, such as the stability of the corresponding output
termediate lemmas from the proof context and Lean error              value.
feedback. Only candidates accepted by the Lean kernel are
added to the lemma pool and reused in subsequent proof tasks.                              IV. E XPERMENTAL
   1) Proof-Task Construction: For each high-level specifi-          A. Expermental set
cation, the system first creates a Lean theorem with an                To evaluate the effectiveness of Rtl2lean in RTL for-
incomplete proof and collects the relevant context, including        mal modeling, theorem generation, and Lean-based machine
the generated state definitions, transition functions, four-layer    checking, we select six SystemVerilog designs with diverse
theorem base, and verified lemmas stored in the lemma pool.          functional and structural characteristics from OpenCores [12],
                            TABLE I                                                          TABLE II
       O PEN C ORES RTL DESIGNS USED IN THE EXPERIMENTS                          E VALUATION METRICS FOR RTL 2 LEAN

  Design                  Main Function                                            Metric                  Symbol
                                                                                   Total theorems          Ntotal
  debounce_edge           Debouncing and edge detection                            High-level properties   Nproperty
  fir_filter              Finite impulse response filtering                        Foundational lemmas     Nlemma
  pwm_generator           Pulse-width modulation                                   Proof success rate      Rproof
                                                                                   End-to-end time         Te2e
  lfsr_crc                LFSR and CRC computation                                 Lean checking time      TLean
  sync_fifo               Synchronous FIFO buffering                               Reusable lemma ratio    Rreuse
  ps2_keyboard            PS/2 keyboard control

                                                                  C. Proof Results and Lemma Reuse Analysis
as shown in Table I. This benchmark suite enables the ap-
plicability of Rtl2lean to be evaluated across different design      Table III presents the proof results and lemma reuse statis-
types and hardware structures. To validate the effectiveness      tics of Rtl2lean on the six RTL designs. Rtl2lean generates
of the proposed method, Lean 4.26 [13] is used to check the       and verifies a total of 403 theorems, including 45 high-
Lean models, foundational lemmas, and high-level properties       level properties and 358 foundational lemmas. Among the
generated by Rtl2lean. All experiments are conducted on a         foundational lemmas, 287 can be automatically reused in
server equipped with an Intel(R) Xeon(R) Gold 6148 CPU            subsequent proofs. All generated theorems are successfully
and 629 GB of RAM.                                                checked by Lean, resulting in a proof success rate of 100%
                                                                  for every design.
B. Evaluation Metrics                                                As shown in Table III, the number of high-level properties
   To evaluate the proof-generation capability, correctness,      remains relatively stable across the evaluated designs, ranging
execution efficiency, and lemma reusability of Rtl2lean, we       from seven to eight, whereas the number of foundational
adopt the metrics summarized in Table II. The total number        lemmas varies considerably, from 22 for fir_filter to
of theorems, denoted by Ntotal , measures the overall scale       86 for sync_fifo. This difference indicates that the size
of the formal verification artifacts generated and checked        of the foundational proof library is mainly affected by the
by Lean. The number of high-level properties, denoted by          complexity of state variables, assignment operations, and state-
Nproperty , indicates the number of RTL functional and state-     update dependencies, rather than solely by the number of high-
related properties verified by the framework. The number of       level properties. In particular, sync_fifo contains more
foundational lemmas, denoted by Nlemma , characterizes the        state and control relations and therefore produces the largest
size of the supporting proof library automatically generated      number of foundational lemmas and total theorems.
for proving these high-level properties.                             All six designs achieve a proof success rate of 100%,
   The proof success rate measures the proportion of generated    demonstrating that the Lean models and proofs generated by
theorems that are successfully accepted by Lean and is defined    Rtl2lean can be successfully machine-checked across designs
as                                                                with different functions and structures. The overall reusable
                                   Nproved
            Proof Success Rate =           × 100%,        (12)    lemma ratio reaches 80.2%, with five designs exceeding 77%,
                                    Ntotal                        indicating that most foundational lemmas can be reused in
where Nproved denotes the number of theorems successfully         subsequent high-level proofs to reduce repeated reasoning
checked by Lean, and Ntotal denotes the total number of           over low-level assignment and state-update semantics. This
generated theorems. We additionally report the numbers of         result also validates the effectiveness of Rtl2lean’s hierarchical
errors, unresolved goals, and proofs containing sorry to          proof structure, in which foundational semantic relations are
identify incomplete verification results.                         proved once and then shared across multiple properties. Note
   For efficiency evaluation, we report the end-to-end exe-       that Rreuse measures the proportion of lemmas available for
cution time, denoted by Te2e , and the Lean checking time,        automatic reuse rather than their exact dynamic usage in
denoted by TLean . The former measures the total time for RTL     individual proofs.
translation, theorem and lemma generation, proof construction,
and result collection, while the latter measures the time         D. Time Overhead
required by Lean to check the generated proof files. We also
                                                                     We measure the end-to-end execution time, Te2e , and the
evaluate the automatic reusability of foundational lemmas by
                                                                  Lean checking time, TLean . The former includes RTL transla-
defining the reusable lemma ratio as
                                                                  tion, theorem and lemma generation, proof construction, and
                            Nreusable                             result collection, while the latter measures the time required
                  Rreuse =            × 100%,             (13)
                            Nlemma                                by Lean to check the generated proof files. Table IV reports
where Nreusable denotes the number of foundational lemmas         the checking time for each design.
that can be automatically applied in subsequent proofs, and          The complete proof-generation pipeline takes only Te2e =
Nlemma denotes the total number of foundational lemmas.           0.650 s for all six designs, since the deterministic proof
                                                                    TABLE III
                                              P ROOF RESULTS AND LEMMA REUSE STATISTICS OF RTL 2 LEAN

                             Design                    Nproperty      Nlemma        Nreusable      Ntotal      Rproof       Rreuse
                             debounce_edge                       8           71             56          79      100%        78.9%
                             fir_filter                          7           22             14          29      100%        63.6%
                             pwm_generator                       7           74             62          81      100%        83.8%
                             lfsr_crc                            7           35             27          42      100%        77.1%
                             sync_fifo                           8           86             70          94      100%        81.4%
                             ps2_keyboard                        8           70             58          78      100%        82.9%
                             Total                             45          358             287        403       100%       80.2%



                                TABLE IV                                           [3] A. Biere, A. Cimatti, E. M. Clarke, and Y. Zhu, “Symbolic model
                       T IME OVERHEAD OF RTL 2 LEAN                                    checking without BDDs,” in Tools and Algorithms for the Construction
                                                                                       and Analysis of Systems, ser. Lecture Notes in Computer Science, W. R.
               Design                   Ntotal     TLean (s)                           Cleaveland, Ed., vol. 1579. Berlin, Heidelberg: Springer, 1999, pp.
                                                                                       193–207.
               debounce_edge                 79        1.113                       [4] E. M. Clarke, W. Klieber, M. Nováček, and P. Zuliani, “Model checking
               fir_filter                    29        0.558                           and the state explosion problem,” in Tools for Practical Software
               pwm_generator                 81        0.918                           Verification, ser. Lecture Notes in Computer Science, B. Meyer and
               lfsr_crc                      42        0.721                           M. Nordio, Eds. Berlin, Heidelberg: Springer, 2012, vol. 7682, pp.
                                                                                       1–30.
               sync_fifo                     94        0.936                       [5] L. de Moura and S. Ullrich, “The Lean 4 theorem prover and pro-
               ps2_keyboard                  78        1.327                           gramming language,” in Automated Deduction – CADE 28, ser. Lecture
               Total                       403         5.573                           Notes in Computer Science, A. Platzer and G. Sutcliffe, Eds., vol. 12699.
                                                                                       Cham: Springer, 2021, pp. 625–635.
                                                                                   [6] J. Choi, M. Vijayaraghavan, B. Sherman, A. Chlipala, and Arvind,
                                                                                       “Kami: A platform for high-level parametric hardware specification and
                                                                                       its modular verification,” Proceedings of the ACM on Programming
templates require neither proof search nor external model calls.                       Languages, vol. 1, no. ICFP, pp. 24:1–24:30, 2017.
In comparison, Lean checking takes 5.573 s in total, indicating                    [7] Project Oak, “Silver Oak: Formal specification and verification of hard-
that most of the time is spent on definition reduction and proof-                      ware,” https://project-oak.github.io/silveroak/, accessed: 2026-07-17.
                                                                                   [8] IEEE, “IEEE Standard for SystemVerilog—Unified Hardware Design,
term checking. Each design is checked in less than 1.4 s,                              Specification, and Verification Language,” Institute of Electrical and
including sync_fifo, which contains the largest number                                 Electronics Engineers, New York, NY, USA, IEEE Standard IEEE Std
of theorems. However, TLean is not strictly proportional to                            1800-2023, Feb. 2024, revision of IEEE Std 1800-2017.
                                                                                   [9] S. Polu and I. Sutskever, “Generative language modeling for automated
Ntotal ; for example, ps2_keyboard requires more checking                              theorem proving,” arXiv preprint arXiv:2009.03393, 2020.
time than sync_fifo despite containing fewer theorems.                            [10] K. Yang, A. M. Swope, A. Gu, R. Chalamala, P. Song, S. Yu, S. Godil,
This suggests that checking cost is also influenced by the                             R. J. Prenger, and A. Anandkumar, “LeanDojo: Theorem proving with
                                                                                       retrieval-augmented language models,” in Advances in Neural Informa-
complexity of state-transition logic and bit-vector expressions.                       tion Processing Systems, vol. 36. Curran Associates, Inc., 2023, pp.
                                                                                       21 573–21 612.
                                                                                  [11] J. Xiong, Q. Han, C. Ding, H. Xiao, Z. Su, C. Tao, and N. Wong,
                           V. C ONCLUSION                                              “CktFormalizer: Autoformalization of natural language into circuit rep-
                                                                                       resentations,” arXiv preprint arXiv:2605.07782, 2026.
   This paper presents Rtl2lean, a framework that translates                      [12] OpenCores, “OpenCores: Free and open-source gateware IP cores,”
                                                                                       https://opencores.org/, online resource, accessed July 18, 2026.
SystemVerilog RTL into executable Lean 4 models, generates                        [13] Lean      FRO,     “Lean      4.26.0     release    notes,”   https://lean-
a hierarchical theorem library, and supports high-level veri-                          lang.org/doc/reference/latest/releases/v4.26.0/, Dec. 2025, released
fication through LLM-assisted lemma generation and Lean-                               December 13, 2025; accessed July 18, 2026.
checked lemma reuse. Experiments on six RTL designs pro-
duce 403 machine-checked theorems with a 100 percent proof
success rate and an 80.2 percent reusable lemma ratio. These
results demonstrate the potential of combining automated RTL
translation, structured theorem generation, and kernel-checked
LLM assistance for scalable hardware verification.

                              R EFERENCES

 [1] H. D. Foster, “Trends in functional verification: A 2014 industry study,”
     in Proceedings of the 52nd Annual Design Automation Conference, ser.
     DAC ’15. New York, NY, USA: Association for Computing Machinery,
     2015, pp. 48:1–48:6.
 [2] E. M. Clarke, T. A. Henzinger, H. Veith, and R. Bloem, Eds., Handbook
     of Model Checking. Cham: Springer, 2018.
