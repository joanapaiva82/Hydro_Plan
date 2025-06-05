fig.add_shape(
    type="line",
    x0=today_str,
    x1=today_str,
    y0=0,
    y1=1,
    xref="x",
    yref="paper",
    line=dict(color="#DB504A", dash="dash")
)
fig.add_annotation(
    x=today_str,
    y=1.02,
    xref="x",
    yref="paper",
    text="Today",
    showarrow=False,
    font=dict(color="#DB504A", size=12)
)
