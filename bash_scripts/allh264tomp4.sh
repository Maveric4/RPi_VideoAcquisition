#!/bin/bash
mkdir mp4
for vid in "./out"/*
do
	path="${vid/h264/"mp4"}"
#	echo $path
	valid_path="${path/out/"mp4"}"
#	echo $valid_path
	MP4Box -add "$vid" "$valid_path"
done

