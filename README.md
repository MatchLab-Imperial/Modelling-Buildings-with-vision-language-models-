# Modelling-Buildings-with-vision-language-models

A lightweight pipeline to extract **building materials, heights, and roof types/conditions** from street-level imagery using modern **vision–language models (VLMs)** plus classic CNN backbones.

---

## Table of Contents
- [Introduction](#introduction)
- [Datasets](#datasets)


---

## Introduction

Urban planners, insurers, and emergency responders increasingly rely on up-to-date information about the **materials, heights, and roof conditions** of buildings, since these attributes drive decisions around safety, maintenance, and risk. This project explores whether modern vision–language models (VLMs) and lightweight fine-tuning pipelines can extract such attributes efficiently from street-level imagery.

We adopt a **segmentation-first** workflow that combines **GroundedSAM** (object-level precision) with **CLIPSeg** (region semantics). The merged masks isolate building regions, which then feed:
- **Material / roof type & condition** classification via **CLIP** fine-tuning or a **YOLOv8** classification head.
- **Height estimation** from depth cues and calibrated geometry, achieving average relative error around **~23%** on our internal benchmarks.

This design blends **zero-shot transfer** with **lightweight adaptation**, keeping the system practical for city-scale deployment. Future work targets **adaptive ensembles** that route images to CLIP/YOLO/SAM variants based on image quality and task difficulty.

---

## Datasets

- **Material**: https://drive.google.com/file/d/1zai-AgnPL19pXVH9MqnFsNIm_qqrXGH-/view?usp=sharing  
- **Height**: https://drive.google.com/file/d/1vKzG0ER-pC8NV535oo7Aa1cRKboI32fh/view?usp=sharing


