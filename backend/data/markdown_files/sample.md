# **Modeling and Synthesizing Idiopathic Facial Paralysis** 

**Maryam Moosaei, Maryam Pourebadi, and Laurel D. Riek** Computer Science and Engineering, UC San Diego 

**_Abstract_ — Over 22 million people worldwide are affected by Parkinson’s disease, stroke, and Bell’s palsy (BP), which can cause facial paralysis (FP). People with FP have trouble having their expressions understood: both laypersons and clinicians have difficulty understanding them and often misinterpret them, which can result in poor social interactions and poor care delivery. One way to address this problem is through better education and training, of which computational tools may prove invaluable. Thus, in this paper, we explore how to build systems that can recognize and synthesize asymmetrical facial expressions. We introduce a novel computational model of asymmetric facial expressions for BP, which we can synthesize on either virtual and robotic patient simulators. We explore this within the context of clinical education, and built a patient simulator with synthesized FP in order to help clinicians perceive facial paralysis in patients. We conducted both computational and human-focused evaluations of the model, including the feedback from clinical experts. Our results suggest that our BP model is realistic, and comparable to the expressions of people with BP. Thus, this work has the potential to provide a practical training tool for clinical learners to better understand the expressions of people with BP. Our work can also help researchers in the facial recognition community to explore new methods for asymmetric facial expression analysis and synthesis.** 

## I. INTRODUCTION 

Every year, 22 million people experience stroke, Parkinson’s disease, Moebius syndrome, and Bell’s Palsy (BP) [1], [23], [39], which can cause facial paralysis (FP). FP is the inability to move one’s facial muscles on the affected side of the face, leading to asymmetric facial expressions [7]. The quality of social interaction that people with asymmetric facial expressions experience can be poor due to others who have difficulty understanding their emotions [10]. Studies show observers perceive the emotions of a person with FP differently from their actual emotional states [36]. For example, people with severe FP are perceived as less happy than people with mild FP [11]. For people with Parkinson’s disease, observers may mistake expressions of happiness, as signifying depression or deception [3], [37]. 

In clinical contexts, these misperceptions can lead to poor care delivery. Healthcare providers frequently have negatively biased impressions of patients with facial nerve paralysis [38], which may adversely affect the quality of care they receive [34], [35]. If a patient and a healthcare provider do not communicate effectively, there is a higher chance that their treatment will be unsuccessful [3], [36]. Therefore, new training tools which enable clinical learners to practice their interaction with FP patients may result in improved care for people with FP, and also improve how clinicians calibrate their perception of asymmetric expressions. 

978-1-7281-0089-0/19/$31.00 _⃝_ c 2019 IEEE 

Virtual and robotic patient simulators are one of the most commonly used training tools in clinical education. They provide clinical learners with a low-risk, high-fidelity learning environment to practice their procedural and communication skills [30]. Robotic patient simulators (RPS), in particular, can convey realistic, immersive training experiences for learners. They are lifelike, patient-sized humanoid robots that can simulate human physiological responses. 

Research suggests that using these simulators may reduce preventable medical errors, which cause approximately 400,000 deaths per year in the US hospitals alone [20], [2]. However, current commercial simulators suffer from a major design flaw: they completely lack facial expressions (see Figure 1). Our team has created expressive virtual and robot patient simulators, which show promise as an important clinical education tool [33], [2], [28], [27]. The development of these simulators was based on the assumption that human faces are structurally symmetric. However, due to the large number of people affected by FP, it is also important to explore the synthesis of asymmetric facial expressions in these contexts. To our knowledge, FP patient simulators have not been explored in this way. Employing simulators in this way may help providers avoid forming biased impressions, improve clinical communication, and, therefore, improve care delivery for people with FP. 

In this paper, we introduce the concept of using masked synthesis on patient simulators in order to model asymmetric facial expressions, situated within a clinical education context. Masks are computational models derived from recognized expressions of real people with FP. Masked synthesis is a process of using pre-built masks based on the face of a person with FP, and overlaying it on the stream of standard performance driven synthesis to recreate the asymmetric facial expressions [27]. The longitudinal goal of our research is to build accurate models of people with asymmetric facial expressions, and to help support clinical engagement with people who have FP. 

The contributions of this paper are twofold. First, we present a novel algorithm to build accurate computational models (masks) of people with BP that are constructible in real time (See Section III) . Second, we applied the algorithm to synthesize BP on virtual patients, and found that clinicians perceive it to be realistic and comparable to humans with BP (See Sections IV and V). 

This work is important for the greater affective computing and patient simulation communities because it allows researchers to explore new methods for synthesizing facial expressions. Moreover, by leveraging the BP patient simulator approach presented in this paper, clinical learners may 



Fig. 1. Left: The simulation center setup where a team of clinical learners treat a non-expressive HPS, which is controlled by simulation operators in a control room. Center: a commonly used inexpressive mannequin head. Right: An example of an expressive RPS system our team built, synthesizing pain. 

have the potential to more accurately diagnose people with BP, and to be better able to interact with them. We discuss the implications of these findings in Section VI) 

## II. BACKGROUND 

Recognizing and synthesizing facial expressions is desirable for a variety of different applications including: human face and head modeling [12], [15], illofacial surgery [9], and rendering robot faces [21]. While there is a significant body of literature exploring symmetric expressions [15], [9], it is also important to study asymmetric facial expressions. 

Researchers have had success in identifying the salient features of asymmetric and restricted facial expressions. For example, Tickle-Degnen et al. [41] designed a study to identify reliable emotional cues from expressive behavior in women and men with Parkinson’s disease. Other researchers proposed different quantitative analysis methods to measure the facial asymmetry of facial images [6], [22], [31], [32]. 

While previous work has laid the foundation for exploring asymmetry, it is critical to study synthesizing asymmetry, especially in clinical education settings. People with asymmetric facial expressions have limited facial expressivity, which makes it difficult for others to form a reliable understanding of their emotions. Moreover, in clinical settings, if a patient and provider cannot communicate effectively, it can adversely affect rapport with the patient and their care decisions [3], [36]. 

Building models to synthesize asymmetric facial expressions on virtual or physical simulator faces may help to improve the social and procedural skills of clinicians and help promote the quality of care they give to patients with BP. Many researchers have worked on both facially expressive virtual simulators [12] and expressive physical robots [33], [26], [2], [29], [27]. Still, there is a lack of work done on developing patient simulators capable of expressing asymmetric facial expressions. 

One of the most commonly used modalities in clinical simulation centers are virtual and robotic patient simulators. Patient simulators help improve clinicians’ procedural and communication skills and enable them to provide effective treatment to patients [28]. These systems provide caregivers 

and clinical learners with a low-risk, high-fidelity, clinicallysimilar learning environment to practice their skills [30]. Although using simulators may reduce preventable medical errors [20], the absence of facial expressions on these simulators may adversely affect patient outcomes [2], [24]. 

To address this issue, we have built both virtual and robotic patient simulators able to express a range of pathologies, including pain and stroke [33], [2]. We also introduced a generalized automatic framework that can accurately map facial expressions from a performer’s face to both simulated and robotic faces in real-time [27], [28]. The method is based on performance-driven synthesis, which maps motions from video of an operator/educator onto the face of an embodiment (e.g., virtual avatar or robot). In our current work, we build on this to explore a new avenue: the recognition and synthesis of asymmetric facial expressions. 

## III. METHODOLOGY 

In our work, we are interested in a particular type of FP, Bell’s Palsy (BP). We explore two main research questions in this work. First, how can we computationally model the facial characteristics of BP and synthesize them on a simulator? This is an important question because answering it would enable the development simulators capable of expressing asymmetric facial expressions. Second, how realistically does our mask model convey signs of BP when synthesized on a virtual patient? Addressing this question will help inform the potential clinical efficacy of such an approach using FP simulators as clinical educational tools. 

We developed a new masked synthesis method for asymmetric facial expressions, and addressed the aforementioned research questions by engaging in the following activities. First, we acquired videos of people with BP and extracted facial features using a CLM-based approach (See Section IIIA). Next, we built computational models (masks) representing the facial characteristics of BP. We then overlaid these prebuilt masks onto a stream of facial expressions generated by standard performance-driven synthesis (See Fig. 2). Next, we transferred the generated asymmetric expressions to the face of a virtual patient simulator(See Section III-B). Finally, we ran an expert-based study to evaluate the realism of the 



Fig. 2. The context for performing masked synthesis. This can be performed on either a virtual or robotic patient simulator. 

synthesized expressions in comparison to actual patients (See Section IV). 

source videos and label the ones that the face tracker can accurately track. We only included the well-tracked videos in our work. 

## _A. BP video acquisition and facial feature extraction_ 

We focused on one example pathology, BP which affects the facial nerve, causing facial weakness and an inability to control the affected side of the face. The facial weakness usually involves eyes, mouth, and forehead (See Fig. 5). 

To build computational models of the facial characteristics of asymmetric expressions, the first step was to acquire source videos from people with BP expressing a wide range of expressions. Therefore, we collected selfrecorded, publically-available videos from people with BP on YouTube. 

Many people who have experienced BP have recorded videos of their experience from their diagnosis to their recovery. In these videos, people convey a wide range of expressions including raising their eyebrow, furrowing their brow, smiling, and closing their affected eye to show how BP affects these expressions and how the condition improves over time. Figure 5 presents some example frames from a source video downloaded from YouTube, and shows how BP affects different facial movements. 

We downloaded ten source videos from YouTube that present people with BP conveying four expressions (raising eyebrow, furrowing brow, smiling, and closing the eye) required for assessing BP. To ensure that these videos have BP, we only downloaded videos in which either people verbally state their BP diagnosis or the video contains a textual tag indicating BP. 

We processed all the source videos to include only ones of high quality in our work (e.g, limited noise and occlusion). Additionally, since the source videos had different lengths, we pre-processed them by cutting them to the same length and only including parts where people were conveying facial expressions. 

To extract facial features, we used a CLM-based face tracker implemented by Baltrusitus et al. [4] to track 68 facial points frame-by-frame from each of the source videos (see Fig. 3). We then asked two human judges to watch all the 

## _B. Build computational models of Bell’s palsy_ 

We built a model for BP inspired by the methods used in the virtual animation literature. Particularly, we have developed our model based on the work by Boker et al. [12], who performed research on manipulating facial expressions and head movements in real time during face to face conversation in video conferencing. Their experiment included two conversants who were sitting in separate rooms, each facing a camera. The researchers used Active Appearance Models (AAMs) [13] to track the facial features of the first conversant. They modified the tracked facial expressions of the first conversant and used them to re-synthesize an avatar with the modified expressions. 

The avatar interacted with the second conversant in a video conference. Second conversants were asked if they noticed anything unusual during the conversation. None of the participants noticed they were talking to a computer-generated avatar and none of them guessed that the expressions were manipulated. 

To modify the expressions, Boker et al. [12] used an AAM-based face tracker. In Active Appearance Models, the shape of the face is defined by a number of landmarks and their interconnectivity, which shapes a triangulated mesh. In other words, shape _s_ is defined by 2D coordinates of _n_ facial landmarks: _s_ = [ _x_ 1 _, y_ 1 _, x_ 2 _, y_ 2 _, ..., xn, yn_ ]<sup>_T_</sup> . These facial landmarks are vertices of the triangulated mesh. 

The training step of AAM models requires manually labeling facial landmarks in some frames and running Principal Component Analysis (PCA) to find the shape model of a face. After the training step, the shape model is defined as below: 



<!-- Start of picture text -->
m<br>s  =  s 0 + � PiSi (1)<br>i =1<br><!-- End of picture text -->

_s_ 0 is the mean shape and the _si_ vectors are the _m_ vectors that show the shape variation of facial landmarks (mesh 



Fig. 3. Comparing the calculated coordinates of feature points with the actual coordinates of the points on the affected side of the face 

vertices) from the mean. The coefficients _pi_ are the shape parameters which define the contribution of each of the shape vectors _si_ in the shape _s_ . Therefore, scaling the _pi_ parameters will exaggerate or attenuate the facial expressions. 



<!-- Start of picture text -->
m<br>s  =  s 0 + � PiSiβi (2)<br>i =1<br><!-- End of picture text -->

_β_ is a scalar which will exaggerate the expressions if it is bigger than one and will attenuate the expressions if it is smaller than one. Boker et al. [12] used _β_ values smaller than one to reduce expressiveness of a conversant. They wanted to study if changing the expressiveness would affect the behavior during a conversation. 

We used a similar approach to build a model for BP. However, in our work, we used a CLM-based face tracker to track 68 facial points. Constrained Local Models (CLM) [14] are similar to Appearance Local Models (AAM) [13] except they do not require manual labeling, and therefore are an improvement over AAMs. Similar to Boker et al. [12], we scaled the CLM parameters by using equation 2. However, instead of attenuating the parameters like Boker et al. [12], we scaled them based on the scaling parameters that we calculated for a pathology (BP) in the following section. 

The CLM-based face tracker that we used in our work tracks 68 facial points frame-by-frame (See Fig. 3). These 68 facial points are vertices of a triangulated mesh. To build the model of a pathology (e.g. BP), we found the 68 scaling parameters for the facial feature points for that pathology. We did this in three steps which are explained below. 

First, we selected a well-tracked source video that included a wide range of facial expressions expressed by a person with BP. From the video, we selected 20 frames in which the asymmetry is most noticeable. 

Second, using the CLM-based face tracker, we tracked 68 facial points in each of the 20 chosen frames. We preprocess the feature points to remove the effect of translation, rotation, and distance to the camera. Then, using the 2D coordinates of the 34 facial features of the unaffected side of the face, we calculated the 2D coordinates of the other part of the face, assuming that the person did not have asymmetric facial expressions. To do so, we used the tip of the nose 

as a reference point. The tip of the nose stays static through transitioning from one facial expression to the other. 

In a person without FP, each facial feature of one side of the face has the same distance to the tip of the nose as its corresponding point on the other side of the face. For example, the left eye corner and the right eye corner each have the same distance to the tip of the nose. In a person with asymmetric facial expressions, this is not true. Therefore, we used the distance from the tip of the nose to calculate the 2D coordinates of 34 feature points on the affected side of the face, assuming the person did not have FP. 

Without loss of generality, assume that the left side of the face is affected by FP. In each frame, we track 2D coordinates of 68 facial features. As seen in Fig. 3, there are 29 feature points on each side of the face and 10 feature points on the line symmetry of a face. Feature points (0 _, . . . ,_ 28) are the 29 points on the right side of the face, feature points (29 _, . . . ,_ 38) are the 10 feature points on the line of symmetry of the face, and feature points (39 _, . . . ,_ 67) are the 29 feature points on the left side of the face. We used feature point _33_ (the tip of the nose) as a reference point. 

After removing the effect of translation and rotation in each frame, _Rx_ and _Ry_ in 3 are two arrays of _x_ and _y_ coordinates of the 29 feature points on the right (unaffected) side of the face. _Lx_ and _Ly_ in 4 are two arrays of _x_ and _y_ coordinates of the 29 feature points on the left (affected) side of the face. 



<!-- Start of picture text -->
Rx = [ x 0 , x 1 , ..., x 28]  , Ry = [ y 0 , y 1 , ..., y 28] (3)<br><!-- End of picture text -->



<!-- Start of picture text -->
Lx = [ x 39 , x 40 , ..., x 67]  , Ly = [ y 39 , y 40 , ..., y 67] (4)<br><!-- End of picture text -->

_L_<sup>_′_</sup> _x_<sup>and</sup><sup>_L′_</sup> _y_<sup>arethetwoarrayswiththeestimated</sup><sup>_x_and</sup><sup>_y_</sup> coordinates of the left (affected) side of the face assuming the person did not have asymmetric facial expressions. 



<!-- Start of picture text -->
L ′ x = [ x′ 38 , x 39 ′ , ..., x 65 ′ ]  , L′ y = [ y 38 ′ , y 39 ′ , ..., y 65 ′ ] (5)<br><!-- End of picture text -->

As Fig. 3 presents: 



<!-- Start of picture text -->
yi ′ =  yi− 38 37  < i <  66 (6)<br><!-- End of picture text -->



<!-- Start of picture text -->
x ′ i = ( x 32 − xi− 38) +  x 32 = 2 x 32 − xi− 38 37  < i <  66<br>(7)<br><!-- End of picture text -->

Third, we compared the calculated coordinates of points from the second step ( _L_<sup>_′_</sup> _x_<sup>and</sup><sup>_L′_</sup> _y_<sup>)withtheactualco-</sup> ordinates of the feature points on the affected side of the face ( _Lx_ and _Ly_ ). Dividing the actual coordinates by the calculated coordinates gave us scaling parameter for _x_ and _y_ coordinates of each of the facial points. Therefore, the scaling parameters, _βi,x_ and _βi,y_ for _x_ and _y_ coordinates of each facial point on the left side of face will be calculated as below: 



<!-- Start of picture text -->
βi,x = x i ′ βi,y = y i ′ , 37  < i <  66 (8)<br>xi yi<br><!-- End of picture text -->



Fig. 4. Sample frames from the stimuli videos. 

All the _βi_ scales are one for the 29 facial points on the unaffected side of the face. All the _βi_ scales are less than one for the 29 facial points on the affected side of the face. This is because FP causes weakness in the affected side of the face and therefore, feature points of that side will have less movement. 

For each feature point on the affected side of the face, we calculated its scaling parameter in all of the frames and averaged them. For our work, we will consider frames with the highest intensity to build our model. Possible future work could be building a model of different pathologies in different stages of the disease with different intensities. 

Additionally, applying the same method on different people with BP may output different scales and yield different models. This is because BP has some idiosyncratic characteristics; although all cases of BP include some degree of weakened mobility on one side of the face, the severity may vary across individuals. Thus, we built three masks using source videos of three people with BP (see Fig. 5). 

## IV. EXPERIMENTAL VALIDATION 

To evaluate our masked synthesis module and get feedback for further refinement, we ran a qualitative, expertbased perceptual experiment. This is a common method for evaluating synthesized facial expressions [8], [25]. Getting initial feedback from clinicians is very valuable because it provides insights for improving the model and exploring its potential for being used as part of an educational tool for clinicians. Additionally, future users of our masked synthesis module are clinicians, and developing an educational tool for clinicians should be an interdisciplinary collaboration involving medical educators and computer scientists [16], [18], [19]. The experts in our study were four clinicians familiar with assessing facial paralysis in BP patients. 

We first collected videos from a performer without BP. As ultimately we want this masked synthesis approach to be 

used by operators without BP in a clinical simulation context (see Fig. 2), it was important to study the likely expressions clinicians would make, and how they would appear when masked. We recorded two sets of videos that are required in BP diagnosis: diagnostic expressions of the eyes, brow, and lower face, and expressions that happen during interviews between clinicians and BP patients. 

In the first set (diagnostic), a performer without BP was recorded while performing five expressions required for assessing paralysis [17]: _closing the eyes_ , _raising the eyebrows_ , _furrowing the brow_ , _smiling_ , and _raising the cheeks_ . The performer was instructed to repeat each expression five times. This resulted in five videos, each about 10 seconds long. 

In the second set (interview), a performer without BP answered a list of questions that a clinician asks when diagnosing a BP patient [17]. Our goal was to record natural expressions that happen during interaction between a BP patient and a clinician. The interview video was 40 seconds long. This yielded five diagnostic video and one interview video. 

From these six source videos, we used a face tracker [5] to track 68 facial points frame-by-frame, and extracted facial features of the performer’s face. We then applied the scaling parameters corresponding to each of the pre-built masks of BP to the extracted feature points of each source video. Since we had six source videos and three pre-built masks, this process gave us 18 sets of masked feature points. 

For each set of masked feature points, we ran the Robot Operating System (ROS) module from [27] to synthesize the masked expressions to a virtual character’s control points for animation in Steam Source SDK. At the end of this step, we had 18 stimuli videos (15 diagnostic stimuli videos of expressions required for assessing BP, and three naturalistic stimuli videos). 



Fig. 5. Sample frames from three people with Bell’s palsy. We used these videos to develop our masks. 

## _A. Case Study_ 

We sought feedback on the realism of our model when applied to a virtual character for synthesizing BP, and how similar the synthesized expressions are to those of real people with BP. We recruited four clinicians (one male and three female) from a US-based medical school. Participants were all native English speakers, and aged between 35 to 59 years old (mean age 48.7 years old). Three of the clinicians were physicians, and one was a clinical nurse. They all had on average 21 years of face-to-face interaction with patients and all had encountered BP patients in their careers. 

We designed a structured online questionnaire to show them our stimuli videos, and ask for their feedback on various aspects of our synthesis results. At the beginning of the study, clinicians received instructions and a brief summary of the project. Next, they watched a video of a real person with BP performing various expressions. We showed them this video to refresh their memory on facial expressions of patients with BP. This video was not used in developing any of the three models. 

We then asked participants questions in two parts. In the first part, they watched the 15 diagnostic stimuli videos in a random order. In each video, a cross-hair was shown for three seconds, followed by a virtual avatar conveying one of 

the expressions required for assessing BP. They then rated the similarity of each avatar’s expressions to those of real BP patients for the entire face, and for that particular facial part (e.g. eyebrows for the raising eyebrow videos). 

The similarity rating was a 4-point Discrete Visual Analogue Scale (DVAS). A one on the scale corresponded to “not at all similar to real patients” and a four on the scale corresponded to “very similar to real patients”. They could watch each video as many times as they need. Figure 4 shows sample frames from the first part of the study. 

In the second part of the study, participants watched the three stimuli videos of naturalistic expressions in a random order. In each video, a cross-hair was shown for three seconds, followed by a virtual avatar conveying natural expressions that would happen during interaction with a clinician. Participants were then asked to rate the similarity of the avatar’s expressions to those of real Bell’s palsy patients overall (entire face), and for each facial part (eyes, eyebrows, cheeks, and mouth) on the same 4-point Discrete Visual Analogue Scale (DVAS). 

Additionally, after watching each naturalistic video, they were asked to provide feedback by answering these openended questions: _“Based on the video you just watched, what aspects did you think were the most realistic?”_ and _“What areas did you think could be improved?”_ . After completing both parts of the study, clinicians were asked to answer these two open-ended questions: _“How useful could this kind of simulation tool used in clinical education?”_ and _“Please share any additional feedback or comments.”_ 

## V. RESULTS 

The overall average score for similarity between the synthesized masked expressions and real patients for the diagnostic expressions was 2.66 (s.d. =0.98). Table I reports the full results for each of the five diagnostic expressions and the entire face. This table suggests that overall clinicians thought that closing eyes and smiling were the most similar expressions to real patients. Cheeks had the lowest overall similarity scores, suggesting that we need to improve our model around the cheeks. 

These similarity scores also show that overall the second mask created more realistic diagnostic expressions. For all the diagnostic expressions (closing eyes, smiling, furrowing brow, and raising cheeks), except raising eyebrows, the second mask outperformed (or was as good as) the other two 

TABLE I 

MEAN SIMILARITY SCORES FOR EACH FACIAL PART AND THE ENTIRE FACE FOR THE DIAGNOSTIC STIMULI VIDEOS ON A 4-POINT DVAS. 

||**Mas**<br>Mean|**k 1**<br>S.D.|**Mas**<br>Mean|**k 2**<br>S.D.|**Mas**<br>Mean|**k 3**<br>S.D.|**Ove**<br>Mean|**rall**<br>S.D.|
|---|---|---|---|---|---|---|---|---|
|**Raising cheeks** (Cheeks)|1.75|0.95|**2.75**|0.95|1.75|0.50|2.08|0.90|
|**Furrowing brow** (Inner eyebrows)|**2.75**|1.25|**2.75**|0.95|**2.75**|1.50|**2.75**|1.13|
|**Closing eyes** (Eyes)|**3.25**|0.95|**3.25**|0.50|2.50|1.29|3.00|0.95|
|**Smiling** (Mouth)|2.50|0.57|**3.50**|0.57|3.00|1.15|3.00|0.85|
|**Raising eyebrows** (Outer eyebrows)|**2.75**|0.95|2.50|1.29|2.25|0.50|2.50|0.90|
|**Overall** (entire face)|2.60|0.99|**2.95**|0.88|2.45|1.05|2.66|0.98|



TABLE II 

MEAN SIMILARITY SCORES FOR THE SYNTHESIZED INTERVIEW EXPRESSIONS ON A 4-POINT DVAS. 

||**Mas**|**k 1**|**Mas**|**k 2**|**Mas**|**k 3**|**Ove**|**rall**|
|---|---|---|---|---|---|---|---|---|
||Mean|S.D.|Mean|S.D.|Mean|S.D.|Mean|S.D.|
|**Cheeks**|2.00|1.00|2.00|1.00|**2.33**|0.57|2.11|0.78|
|**Eyebrows**|2.33|0.57|2.66|0.57|**3.00**|1.00|2.66|0.70|
|**Eyes**|**3.66**|0.57|3.33|0.57|3.33|1.15|3.44|0.72|
|**Mouth**|2.33|0.57|2.00|1.00|**2.66**|1.15|2.33|0.86|
|**Overall** (entire face)|2.66|0.57|2.66|0.57|**3.33**|0.57|2.88|0.60|



models. This suggests that before using the second model in a larger study, its appearance around the eyebrows needs improvement. 

For the naturalistic expression videos, we were only able to include the ratings from three of the clinicians as one was not able to participate in the second part of our study. Table II reports the full results for the naturalistic expressions. For the entire face, and all the facial parts except eyes, the third mask created natural expressions that are more similar to real BP patients. This table also suggests that overall clinicians thought that eyes were the most similar part of the face to real patients and cheeks were the least similar part of the face to real BP patients. 

## VI. DISCUSSION 

The work described in this paper is the first step towards building a complete, expressive patient simulator system capable of recognizing and synthesizing asymmetric facial expressions. Our work addresses the aforementioned gap in the literature by providing clinical learners with a training tool to practice their procedural and communication skills. In this paper, we introduced methods for modelling and synthesizing asymmetric facial expressions associated with BP, and experimentally validated our approach within a clinical education context. 

Our experimental results are encouraging, and suggest that these techniques can be useful in affective computing, clinical education, and related fields. Our proposed algorithm generated a reliable computational model of BP. Moreover, our synthesis method is also suitable for use in real-time clinical simulation and training contexts. We were able to generate realistic face models conveying asymmetric facial expressions. 

There are several ways to further enhance the models and techniques described. First, employing more control points can make the models more realistic. The avatar used in this work did not have any control points for creating wrinkles around the cheeks and nose. This led clinicians to select low ratings for the similarity of the expressions around the avatar’s cheeks, when assessing both the diagnostic and the naturalistic expressions. Clinicians also suggested that adding control points for the eyes could increase the realism of the model, since the affected eyeball of people with BP often rolls into their head when they try to blink. 

Second, we can explore including static asymmetry (e.g., facial drooping) to the synthesized expressions in future 

experiments. Clinicians recommended adding forehead lines to create a more realistic furrowed brow expression, making it possible to recognize the intensity of BP. Moreover, they mentioned that adding “puffing out the cheeks” to the diagnostic set can also improve the expressions, as they are useful for assessing asymmetry of the mouth and lips. 

Third, ideally, we can create a general model for BP that encompasses all the predominant features of BP in order to generally represent all BP patients. If we have enough input source videos of people with BP, we may be able to extract the common features of this specific pathology to create one general BP model. Similarly, if datasets for other pathologies become publicly available, we could also extend this technique to them (e.g., stroke, dystonia). 

Finally, we ultimately want to run a similar experiment with clinical learners using an expressive RPS. This may help clinicians avoid forming biased impressions of people with FP and improve their cultural competency. Also, it may improve their skills in understanding the emotions of people with asymmetric facial expressions, which can lead to better health outcomes and reduce health disparities. 

Our work is important for the affective computing and robotics communities because it allows researchers to explore new methods of facial expression synthesis. For example, our work can be used in teleconferencing or animation to control and manipulate the expressions and identity of a virtual character. It can also be used in computer games, to mask the identity or expressions of a user, or in social assistive robots to be used to support health and well being. 

Overall, this work makes contributions to both interactions with virtual humans, and the study of clinical conditions that alter expressive behaviour, which are two critical applications of facial expression analysis [40]. More specifically, the exploration of recognizing and synthesizing asymmetric facial expressions have significant implications for human emotion analysis. 

## ACKNOWLEDGEMENTS 

This material is based upon work supported by the National Science Foundation under Grant No. IIS-1253935. 

## REFERENCES 

> [1] _The world health report 2002: reducing risks, promoting healthy life_ . World Health Organization, 2002. 

> [2] Using facially expressive robots to calibrate clinical pain perception. In _Proceedings of the 2017 ACM/IEEE International Conference on Human-Robot Interaction_ , 2017. 

- [3] R. C. Arkin and M. J. Pettinati. Moral emotions, robots, and their role in managing stigma in early stage parkinsons disease caregiving. In _Workshop on New Frontiers of Service Robotics for the Eldery, RO-MAN_ , 2014. 

- [4] T. Baltrusaitis, P. Robinson, and L. Morency. 3d constrained local model for rigid and non-rigid facial tracking. In _IEEE Conference on Computer Vision and Pattern Recognition (CVPR)_ , 2012. 

- [5] T. Baltruˇsaitis, P. Robinson, and L. Morency. Openface: an open source facial behavior analysis toolkit. In _IEEE Winter Conference on Applications of Computer Vision (WACV)_ , 2016. 

- [6] A. Bandini, J. Green, B. Richburg, and Y. Yunusova. Automatic detection of orofacial impairment in stroke. In _Proc. Interspeech 2018_ , 2018. 

- [7] R. F. Baugh, G. J. Basura, L. E. Ishii, S. R. Schwartz, C.M. Drumheller, and R. Burkholder. Clinical practice guideline bells palsy. _Otolaryngology–Head and Neck Surgery_ , 2013. 

- [8] C. Becker-Asano and H. Ishiguro. Evaluating facial displays of emotion for the android robot Geminoid F. In _IEEE Workshop on Affective Computational Intelligence (WACI)_ , 2011. 

- [9] M. Benz, X. Laboureux, T. Maier, E. Nkenke, S. Seeger, F. Neukam, and G. Husler. The symmetry of faces. 2002. 

- [10] K. R. Bogart and L. Tickle-Degnen. Looking beyond the face: A training to improve perceivers impressions of people with facial paralysis. _Patient education and counseling_ , 2015. 

- [11] K. R. Bogart, L. Tickle-Degnen, and N. Ambady. Communicating without the face: Holistic perception of emotions of people with facial paralysis. _Basic and Applied Social Psychology_ , 2014. 

- [12] S. M. Boker, J. F. Cohn, B. Theobald, I. Matthews, T. R. Brick, and J. R. Spies. Effects of damping head movement and facial expression in dyadic conversation using real–time facial expression tracking and synthesized avatars. _Philosophical Transactions of the Royal Society of London B: Biological Sciences_ , 2009. 

- [13] T. F. Cootes, G. J. Edwards, and C. J. Taylor. Active appearance models. _IEEE Trans. Pattern Anal. Mach. Intell._ , 1998. 

- [14] D. Cristinacce and T. F. Cootes. Feature detection and tracking with constrained local models. Pattern Recognition, 2006. 

- [15] H. Dai, N. Pears, W. Smith, and C. Duncan. Symmetric shape morphing for 3d face and head modelling. In _2018 13th IEEE International Conference on Automatic Face Gesture Recognition (FG 2018)_ , 2018. 

- [16] A. M. Deladisma, M. Cohen, A. Stevens, P. Wagner, B. Lok, T. Bernard, C. Oxendine, L. Schumacher, K. Johnsen, R. Dickerson, et al. Do medical students respond empathetically to a virtual patient? _The American Journal of Surgery_ , 2007. 

- [17] T. J. Eviston, G. R. Croxson, P. G. Kennedy, T. Hadlock, and A. V. Krishnan. Bell’s palsy: aetiology, clinical features and multidisciplinary care. _Journal of Neurology, Neurosurgery & Psychiatry_ , 2015. 

- [18] M. J. Gonzales, V. C. Cheung, and L. D. Riek. Designing collaborative healthcare technology for the acute care workflow. In _Proceedings of the 9th International Conference on Pervasive Computing Technologies for Healthcare_ , 2015. 

- [19] M. J Gonzales, J. M. Henry, A. W. Calhoun, and L. D. Riek. Visual TASK: A collaborative cognitive aid for acute care resuscitation. _10th EAI International Conference on Pervasive Computing Technologies for Healthcare (Pervasive Health)_ , 2016. 

   - [26] M. Moosaei, M. J. Gonzales, and L. D. Riek. Naturalistic pain synthesis for virtual patients. In _International Conference on Intelligent Virtual Agents_ , 2014. 

   - [27] M. Moosaei, C. J. Hayes, and L. D. Riek. Facial expression synthesis on robots: An ros module. _Proceedings of the Tenth Annual ACM/IEEE International Conference on Human-Robot Interaction_ , 2015. 

   - [28] M. Moosaei, C. J. Hayes, and L. D. Riek. Performing facial expression synthesis on robot faces: A real-time software system. _In Proceedings of the 4th International AISB Symposium on New Frontiers in HumanRobot Interaction, AISB_ , 2015. 

   - [29] M. Moosaei, C. J. Hayes, and L. D. Riek. Performing facial expression synthesis on robot faces: A real-time software system. _In Proceedings of the 4th International AISB Symposium on New Frontiers in HumanRobot Interaction, AISB_ , 2015. 

   - [30] P. Morton. Creating a laboratory that simulates the critical care environment. _Critical Care Nursing, 16(6), 7681. National Association for Associate Degree Nursing_ , 1995. 

   - [31] T. H. Ngo, Y. Chen, M. Seo, N. Matsushiro, and W. Xiong. Quantitative analysis of facial paralysis based on three-dimensional features. In _2016 IEEE International Conference on Image Processing (ICIP)_ , 2016. 

   - [32] T. H. Ngo, M. Seo, Y. Chen, and N. Matsushiro. Quantitative evaluation of facial paralysis using tracking method. In _The 2015 IEEE RIVF International Conference on Computing Communication Technologies - Research, Innovation, and Vision for Future (RIVF)_ , 2015. 

   - [33] M. Pourebadi and L. D. Riek. Expressive robotic patient simulators for clinical education. 2018. 

   - [34] L. D. Riek and P. Robinson. Using robots to help people habituate to visible disabilities. In _IEEE International Conference on Rehabilitation Robotics (ICORR)_ , 2011. 

   - [35] K. L. Robey, P. M. Minihan, L. M. Long-Bellil, J. E. Hahn, J. G. Reiss, G. E. Eddey, Alliance for Disability in Health Care Education, et al. Teaching health care students about disability within a cultural competency context. _Disability and Health Journal_ , 2013. 

   - [36] H. Sunvisson, B. Habermann, S. Weiss, and P. Benner. Augmenting the cartesian medical discourse with an understanding of the person’s lifeworld, lived body, life story and social identity. _Nursing Philosophy_ , 2009. 

   - [37] L. Tickle-Degnen, M. Scheutz, and R. C. Arkin. Collaborative robots in rehabilitation for social self-management of health. 2014. 

   - [38] L. Tickle-Degnen, L. A. Zebrowitz, and H. Ma. Culture, gender and health care stigma: Practitioners response to facial masking experienced by people with parkinsons disease. _Social Science & Medicine_ , 2011. 

   - [39] O. Tysnes and A. Storstein. Epidemiology of parkinson’s disease. _Journal of Neural Transmission_ , 2017. 

   - [40] M. Valstar. Automatic behaviour understanding in medicine. In _Proceedings of the 2014 Workshop on Roadmapping the Future of Multimodal Interaction Research Including Business Opportunities and Challenges_ , 2014. 

   - [41] S. Wang and L. Tickle-Degnen. Emotional cues from expressive behavior of women and men with parkinsons disease. _PloS one_ , 2018. 

- [20] J. T. James. A new evidence-based estimate of patient harms associated with hospital care. _Journal of patient safety_ , 2013. 

- [21] A. Kalegina, G. Schroeder, A. Allchin, K. Berlin, and M. Cakmak. Characterizing the design space of rendered robot faces. In _Proceedings of the 2018 ACM/IEEE International Conference on HumanRobot Interaction_ , 2018. 

- [22] Y. Kihara, G. Duan, T. Nishida, N. Matsushiro, and Y. Chen. A dynamic facial expression database for quantitative analysis of facial paralysis. In _2011 6th International Conference on Computer Sciences and Convergence Information Technology (ICCIT)_ , 2011. 

- [23] A. G. Marson and R. Salinas. Clinical evidence: Bell’s palsy. _Western Journal of Medicine_ , 2000. 

- [24] T. J. Martin, A. P. Rzepczynski, and L. D. Riek. Ask, inform, or act: communication with a robotic patient before haptic action. In _Proceedings of the seventh annual ACM/IEEE international conference on Human-Robot Interaction_ , 2012. 

- [25] D. Mazzei, N. Lazzeri, D. Hanson, and D. De Rossi. Hefes: An hybrid engine for facial expressions synthesis to control human-like androids and avatars. In _IEEE RAS & EMBS International Conference on Biomedical Robotics and Biomechatronics (BioRob)_ , 2012. 

