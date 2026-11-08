ss=q.steps();ss[2]['inputParams']['contentData']='F183超规行李办理说明：请凭临时业务号前往F2_TEST_GATE，核验重量与尺寸，按承运人现场政策办理托运并遵守安全须知。'
q.config('F183_UI_GOAL',steps=ss)
q.config('T2值机岛',steps=ss)
q.save();result={'prepared':True}
